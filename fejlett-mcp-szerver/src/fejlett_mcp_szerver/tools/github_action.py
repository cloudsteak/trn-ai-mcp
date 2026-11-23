"""GitHub Action létezése, legfrissebb stabil verziója és a commit SHA.

A stabil verzió a legmagasabb GitHub-kiadás, ami nem draft és nem előzetes,
és a címkéjén megvan az action.yml vagy az action.yaml. A SHA a címke
commitja: ezt érdemes a workflow uses sorába pinelni.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)

_API = "https://api.github.com"
_TIMEOUT_S = 15
_PAGE = 100
_MAX_TAG_PAGES = 10
_MAX_RELEASE_PAGES = 3
_SHA = re.compile(r"^[0-9a-fA-F]{7,40}$")
_STABLE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"
)
_MAJOR = re.compile(r"^v?(?P<major>0|[1-9]\d*)$")
_MINOR = re.compile(r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)$")
_NAME = re.compile(r"[A-Za-z0-9_.-]+")


class GitHubApi(Protocol):
    def get(self, path: str, query: dict[str, str] | None = None) -> tuple[int, Any]: ...


class GitHubError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True, order=True)
class SemVer:
    major: int
    minor: int
    patch: int


@dataclass(frozen=True)
class TagInfo:
    name: str
    sha: str
    semver: SemVer | None
    major: int | None


@dataclass(frozen=True)
class ActionRef:
    owner: str
    repo: str
    path: str
    ref: str | None

    @property
    def slug(self) -> str:
        if self.path:
            return f"{self.owner}/{self.repo}/{self.path}"
        return f"{self.owner}/{self.repo}"


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self._token = token or None

    @classmethod
    def from_env(cls) -> GitHubClient:
        token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN") or ""
        return cls(token.strip() or None)

    def get(self, path: str, query: dict[str, str] | None = None) -> tuple[int, Any]:
        url = _API + path
        if query:
            url = f"{url}?{urlencode(query)}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "fejlett-mcp-szerver",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=_TIMEOUT_S) as response:
                status = response.status
                raw = response.read()
        except HTTPError as exc:
            status = exc.code
            raw = exc.read()
        except (URLError, TimeoutError, OSError) as exc:
            raise GitHubError(f"A GitHub API nem elérhető: {exc}") from exc
        if not raw:
            return status, None
        try:
            return status, json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise GitHubError("A GitHub API nem JSON választ adott.") from exc


def parse_action(action: str, verzio: str = "") -> ActionRef:
    text = action.strip().strip("`")
    text = re.sub(r"^-\s*", "", text)
    text = re.sub(r"^uses:\s*", "", text, flags=re.IGNORECASE)
    text = text.strip().strip("\"'`")
    text = re.sub(r"\s+#.*$", "", text).strip()
    ref_in_action = ""
    if "@" in text:
        text, ref_in_action = text.rsplit("@", 1)
        ref_in_action = ref_in_action.strip()
    parts = [part for part in text.split("/") if part]
    if len(parts) < 2 or any(not _NAME.fullmatch(part) for part in parts):
        raise ValueError(
            "Érvénytelen action. Így add meg: owner/repo, például actions/checkout."
        )
    owner, repo, *path_parts = parts
    explicit = verzio.strip()
    ref = explicit or ref_in_action or None
    return ActionRef(owner, repo, "/".join(path_parts), ref)


def parse_semver(name: str) -> SemVer | None:
    match = _STABLE.fullmatch(name)
    if not match:
        return None
    return SemVer(int(match["major"]), int(match["minor"]), int(match["patch"]))


def parse_major(name: str) -> int | None:
    match = _MAJOR.fullmatch(name)
    if not match:
        return None
    return int(match["major"])


def inspect_action(action: str, verzio: str = "", client: GitHubApi | None = None) -> str:
    try:
        ref = parse_action(action, verzio)
    except ValueError as exc:
        return str(exc)
    github = client if client is not None else GitHubClient.from_env()
    try:
        return _inspect(ref, github)
    except GitHubError as exc:
        return exc.message


def _inspect(ref: ActionRef, client: GitHubApi) -> str:
    status, body = client.get(_repo(ref))
    if status == 404:
        return _missing(ref)
    failure = _api_failure(status, body)
    if failure:
        return f"action: {ref.slug}\n{failure}"

    repo = _repo(ref)
    tags = _tags(_pages(client, f"{repo}/tags", _MAX_TAG_PAGES))
    stable_names, blocked = _release_sets(
        _pages(client, f"{repo}/releases", _MAX_RELEASE_PAGES)
    )
    candidates = _ordered_candidates(tags, stable_names, blocked)
    latest, skipped = _working_stable(client, ref, candidates)
    if latest is None and not _action_file(client, ref, None):
        text = _not_action(ref)
        if skipped:
            text += "\n" + _skipped(skipped)
        return text

    lines = [f"action: {ref.slug}", "létezik: igen"]
    if latest is None:
        lines.append("legfrissebb stabil: nincs")
        lines.append("Nincs olyan kiadás, ami stabil és tartalmaz action fájlt.")
        if skipped:
            lines.append(_skipped(skipped))
        return "\n".join(lines)

    major = _major_tag(tags, latest)
    lines.append(f"legfrissebb stabil: {latest.name}")
    if major is not None and major.name != latest.name:
        lines.append(f"főverzió: {major.name}")
    lines.append(f"sha: {latest.sha}")
    if skipped:
        lines.append(_skipped(skipped))
    if ref.ref:
        lines.extend(_given(ref, client, tags, candidates, latest))
    lines.append(f"pin: {_pin(ref.slug, latest.sha, latest.name)}")
    return "\n".join(lines)


def _missing(ref: ActionRef) -> str:
    return f"action: {ref.slug}\nlétezik: nem\nA GitHubon nincs ilyen repó."


def _not_action(ref: ActionRef) -> str:
    return (
        f"action: {ref.slug}\n"
        "létezik: nem\n"
        "A repó létezik, de ezen az útvonalon nincs action.yml vagy action.yaml."
    )


def _skipped(names: list[str]) -> str:
    return "kihagyva: " + ", ".join(names) + " (nincs action fájl)"


def _pin(slug: str, sha: str, version: str) -> str:
    return f"{slug}@{sha} # {version}"


def _repo(ref: ActionRef) -> str:
    return f"/repos/{quote(ref.owner, safe='')}/{quote(ref.repo, safe='')}"


def _api_failure(status: int, body: Any) -> str | None:
    if status == 200:
        return None
    message = body.get("message", "") if isinstance(body, dict) else ""
    lowered = message.lower()
    if status in {403, 429} and "rate limit" in lowered:
        return (
            "A GitHub API limitje betelt. "
            "A GITHUB_PERSONAL_ACCESS_TOKEN változóval több kérés fér el."
        )
    if status in {401, 403}:
        return "A GitHub API elutasította a kérést. Ellenőrizd a tokent."
    if status == 404:
        return "A GitHubon nincs ilyen repó."
    return f"A GitHub API hibát adott ({status})."


def _pages(client: GitHubApi, path: str, limit: int) -> list[Any]:
    items: list[Any] = []
    for page in range(1, limit + 1):
        status, body = client.get(path, {"per_page": str(_PAGE), "page": str(page)})
        failure = _api_failure(status, body)
        if failure:
            raise GitHubError(failure)
        if not isinstance(body, list):
            raise GitHubError("A GitHub API nem listát adott.")
        items.extend(body)
        if len(body) < _PAGE:
            break
    return items


def _tags(raw: list[Any]) -> list[TagInfo]:
    tags: list[TagInfo] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        commit = item.get("commit") or {}
        sha = commit.get("sha") if isinstance(commit, dict) else None
        if not isinstance(name, str) or not isinstance(sha, str):
            continue
        semver = parse_semver(name)
        major = None if semver is not None else parse_major(name)
        tags.append(TagInfo(name=name, sha=sha.lower(), semver=semver, major=major))
    return tags


def _release_sets(raw: list[Any]) -> tuple[set[str], set[str]]:
    stable: set[str] = set()
    blocked: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("tag_name")
        if not isinstance(name, str):
            continue
        if item.get("draft") or item.get("prerelease"):
            blocked.add(name)
        else:
            stable.add(name)
    return stable, blocked


def _ordered_candidates(
    tags: list[TagInfo], stable_names: set[str], blocked: set[str]
) -> list[TagInfo]:
    by_name = {tag.name: tag for tag in tags}
    semver_releases = [
        name for name in stable_names if name not in blocked and parse_semver(name) is not None
    ]
    if semver_releases:
        return _rank_semver(by_name, semver_releases)
    major_releases = [
        name for name in stable_names if name not in blocked and parse_major(name) is not None
    ]
    if major_releases:
        return _rank_major(by_name, major_releases)
    semver_tags = [tag for tag in tags if tag.semver is not None and tag.name not in blocked]
    if semver_tags:
        return sorted(semver_tags, key=lambda tag: tag.semver or SemVer(0, 0, 0), reverse=True)
    major_tags = [tag for tag in tags if tag.major is not None and tag.name not in blocked]
    return sorted(major_tags, key=lambda tag: tag.major or 0, reverse=True)


def _rank_semver(by_name: dict[str, TagInfo], names: list[str]) -> list[TagInfo]:
    ranked = sorted(names, key=lambda name: parse_semver(name) or SemVer(0, 0, 0), reverse=True)
    result: list[TagInfo] = []
    for name in ranked:
        semver = parse_semver(name)
        known = by_name.get(name)
        sha = known.sha if known is not None else ""
        result.append(TagInfo(name, sha, semver, None))
    return result


def _rank_major(by_name: dict[str, TagInfo], names: list[str]) -> list[TagInfo]:
    ranked = sorted(names, key=lambda name: parse_major(name) or 0, reverse=True)
    result: list[TagInfo] = []
    for name in ranked:
        major = parse_major(name)
        known = by_name.get(name)
        sha = known.sha if known is not None else ""
        result.append(TagInfo(name, sha, None, major))
    return result


def _action_file(client: GitHubApi, ref: ActionRef, version_ref: str | None) -> bool:
    query = {"ref": version_ref} if version_ref else None
    for filename in ("action.yml", "action.yaml"):
        status, body = client.get(_contents_path(ref, filename), query)
        if status == 200 and isinstance(body, dict) and body.get("type") in {"file", "symlink"}:
            return True
        if status not in {200, 404}:
            failure = _api_failure(status, body)
            if failure:
                raise GitHubError(failure)
    return False


def _contents_path(ref: ActionRef, filename: str) -> str:
    relative = f"{ref.path}/{filename}" if ref.path else filename
    quoted = "/".join(quote(part, safe="") for part in relative.split("/") if part)
    return f"{_repo(ref)}/contents/{quoted}"


def _fill(client: GitHubApi, ref: ActionRef, tag: TagInfo) -> TagInfo:
    if tag.sha:
        return tag
    sha = _resolve_commit(client, ref, tag.name)
    return TagInfo(tag.name, sha, tag.semver, tag.major)


def _working_stable(
    client: GitHubApi, ref: ActionRef, candidates: list[TagInfo]
) -> tuple[TagInfo | None, list[str]]:
    skipped: list[str] = []
    for tag in candidates:
        if _action_file(client, ref, tag.name):
            return _fill(client, ref, tag), skipped
        skipped.append(tag.name)
        if len(skipped) >= 8:
            break
    return None, skipped


def _major_tag(tags: list[TagInfo], precise: TagInfo) -> TagInfo | None:
    if precise.semver is None:
        return None
    prefix = "v" if precise.name.startswith("v") else ""
    wanted = f"{prefix}{precise.semver.major}"
    bare = str(precise.semver.major)
    for name in (wanted, bare):
        for tag in tags:
            if tag.name == name and tag.sha == precise.sha:
                return tag
    return None


def _tags_at_sha(tags: list[TagInfo], sha: str) -> list[TagInfo]:
    needle = sha.lower()
    return [tag for tag in tags if tag.sha == needle]


def _precise(tags: list[TagInfo]) -> TagInfo | None:
    full = [tag for tag in tags if tag.semver is not None]
    if full:
        return max(full, key=lambda tag: tag.semver or SemVer(0, 0, 0))
    if tags:
        return tags[0]
    return None


def _canonical_ref(ref: str) -> str:
    text = ref.strip()
    for prefix in ("refs/tags/", "refs/heads/"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    if len(text) >= 2 and text[0] in {"v", "V"} and text[1].isdigit():
        return "v" + text[1:]
    return text


def _find_tag(tags: list[TagInfo], name: str) -> TagInfo | None:
    exact = {tag.name: tag for tag in tags}
    folded = {tag.name.lower(): tag for tag in tags}
    if name in exact:
        return exact[name]
    if name.lower() in folded:
        return folded[name.lower()]
    alt = name[1:] if name.startswith("v") else f"v{name}"
    if alt in exact:
        return exact[alt]
    if alt.lower() in folded:
        return folded[alt.lower()]

    minor = _MINOR.fullmatch(name)
    if minor is not None:
        major = int(minor["major"])
        minor_n = int(minor["minor"])
        matches = [
            tag
            for tag in tags
            if tag.semver is not None
            and tag.semver.major == major
            and tag.semver.minor == minor_n
        ]
        if matches:
            return max(matches, key=lambda tag: tag.semver or SemVer(0, 0, 0))

    major_match = _MAJOR.fullmatch(name)
    if major_match is None:
        return None
    number = int(major_match["major"])
    for candidate in (name, f"v{number}", str(number)):
        tag = exact.get(candidate)
        if tag is not None and tag.major == number:
            return tag
    matches = [tag for tag in tags if tag.semver is not None and tag.semver.major == number]
    if matches:
        return max(matches, key=lambda tag: tag.semver or SemVer(0, 0, 0))
    return None


def _resolve_commit(client: GitHubApi, ref: ActionRef, name: str) -> str:
    status, body = client.get(f"{_repo(ref)}/commits/{quote(name, safe='')}")
    if status == 422:
        raise GitHubError("A SHA több commitra illik. Add meg hosszabban.")
    if status == 404:
        raise GitHubError(f"Nincs ilyen commit: {name}")
    failure = _api_failure(status, body)
    if failure:
        raise GitHubError(failure)
    if not isinstance(body, dict) or not isinstance(body.get("sha"), str):
        raise GitHubError("A GitHub API nem commitot adott.")
    return str(body["sha"]).lower()


def _given(
    ref: ActionRef,
    client: GitHubApi,
    tags: list[TagInfo],
    candidates: list[TagInfo],
    latest: TagInfo,
) -> list[str]:
    assert ref.ref is not None
    raw = ref.ref.strip()
    if _SHA.fullmatch(raw):
        return _given_sha(ref, client, tags, candidates, latest, raw)
    return _given_version(ref, client, tags, candidates, latest, _canonical_ref(raw), raw)


def _given_sha(
    ref: ActionRef,
    client: GitHubApi,
    tags: list[TagInfo],
    candidates: list[TagInfo],
    latest: TagInfo,
    raw: str,
) -> list[str]:
    if len(raw) == 40 and _tags_at_sha(tags, raw):
        full = raw.lower()
    else:
        full = _resolve_commit(client, ref, raw)
    precise = _precise(_tags_at_sha(tags, full))
    lines = [f"megadott sha: {full}"]
    if precise is None:
        lines.append("megadott verzió: nincs hozzá címke")
        lines.append(_recommend(latest))
        return lines
    lines.append(f"megadott verzió: {precise.name}")
    lines.extend(_advice(precise.name, precise, latest, candidates, client, ref, moving=False))
    return lines


def _given_version(
    ref: ActionRef,
    client: GitHubApi,
    tags: list[TagInfo],
    candidates: list[TagInfo],
    latest: TagInfo,
    name: str,
    raw: str,
) -> list[str]:
    tag = _find_tag(tags, name)
    if tag is None:
        try:
            sha = _resolve_commit(client, ref, name)
        except GitHubError as exc:
            if not exc.message.startswith("Nincs ilyen commit"):
                raise
            return [
                f"megadott: {raw}",
                f"A megadott verzió nem létezik: {raw}",
                _recommend(latest),
            ]
        return [
            f"megadott: {raw}",
            f"megadott sha: {sha}",
            (
                f"frissítés: a {raw} ág, nem kiadás. "
                f"Erre érdemes frissíteni: {latest.name} (sha: {latest.sha})."
            ),
        ]

    precise = _precise(_tags_at_sha(tags, tag.sha)) or tag
    lines = [f"megadott: {tag.name}"]
    if precise.name != tag.name:
        lines.append(f"pontos verzió: {precise.name}")
    lines.append(f"megadott sha: {tag.sha}")
    lines.extend(
        _advice(
            tag.name,
            precise,
            latest,
            candidates,
            client,
            ref,
            moving=tag.major is not None,
        )
    )
    return lines


def _recommend(latest: TagInfo) -> str:
    return f"frissítés: erre érdemes frissíteni: {latest.name} (sha: {latest.sha})."


def _is_older(precise: TagInfo, latest: TagInfo) -> bool | None:
    if precise.sha == latest.sha:
        return None
    if precise.semver is not None and latest.semver is not None:
        if precise.semver == latest.semver:
            return None
        return precise.semver < latest.semver
    left = precise.semver.major if precise.semver is not None else precise.major
    right = latest.semver.major if latest.semver is not None else latest.major
    if left is None or right is None or left == right:
        return None
    return left < right


def _same_major(candidates: list[TagInfo], precise: TagInfo) -> TagInfo | None:
    major = precise.semver.major if precise.semver is not None else precise.major
    if major is None:
        return None
    matches = [
        tag for tag in candidates if tag.semver is not None and tag.semver.major == major
    ]
    if not matches:
        return None
    return max(matches, key=lambda tag: tag.semver or SemVer(0, 0, 0))


def _worth_same(precise: TagInfo, latest: TagInfo, same: TagInfo) -> bool:
    if same.name == latest.name or (same.sha and same.sha == precise.sha):
        return False
    if precise.semver is not None and same.semver is not None and same.semver <= precise.semver:
        return False
    return True


def _advice(
    given_name: str,
    precise: TagInfo,
    latest: TagInfo,
    candidates: list[TagInfo],
    client: GitHubApi,
    ref: ActionRef,
    *,
    moving: bool,
) -> list[str]:
    if precise.sha == latest.sha:
        if moving and given_name != latest.name:
            return [
                "frissítés: ez a legfrissebb stabil verzió. "
                f"A {given_name} mozgó címke; a pin a {latest.name} sha-ja."
            ]
        return ["frissítés: ez a legfrissebb stabil verzió."]

    older = _is_older(precise, latest)
    target = f"{latest.name} (sha: {latest.sha})"
    if older is True:
        line = f"frissítés: {precise.name} régebbi. Erre érdemes frissíteni: {target}."
    elif older is False:
        line = (
            f"frissítés: {precise.name} újabb, mint a legutóbbi stabil kiadás "
            f"({latest.name}). Stabil pinnek ezt érdemes használni: {target}."
        )
    else:
        line = f"frissítés: erre érdemes frissíteni: {target}."
    lines = [line]
    same = _same_major(candidates, precise)
    if same is not None and _worth_same(precise, latest, same):
        if not same.sha:
            same = _fill(client, ref, same)
        if _worth_same(precise, latest, same):
            lines.append(f"ugyanazon főverzió: {same.name} (sha: {same.sha})")
    return lines


def register(mcp: MCPServer) -> None:
    @mcp.tool(title="GitHub Action")
    def github_action(action: str, verzio: str = "") -> str:
        """Ellenőrzi, hogy egy GitHub Action létezik-e, és megadja a legfrissebb stabil verzióját.

        A stabil verzió a legmagasabb kiadás, ami nem draft és nem előzetes, és a címkéjén
        megvan az action.yml. A válasz a pontos verzió (v7.0.1), a főverzió (v7), ha az
        ugyanaz a commit, és a commit SHA.

        Ha verziót vagy SHA-t is adsz, megmondja, mire érdemes frissíteni. Verzióból SHA-t,
        SHA-ból verziót old fel.

        Args:
            action: owner/repo vagy owner/repo/útvonal. Lehet uses: sor, @verzió vagy @sha is.
            verzio: Verzió (v4.2.2, 4.2.2, v4) vagy commit SHA. Üresen a legfrissebb jön.
                Ha az actionben is van @ref, ez felülírja.
        """
        logger.info("github_action action=%s verzio=%s", action, verzio)
        return inspect_action(action, verzio)
