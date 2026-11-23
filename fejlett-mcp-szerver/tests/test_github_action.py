from email.message import EmailMessage
from io import BytesIO
from urllib.error import HTTPError

import pytest

from fejlett_mcp_szerver.tools.github_action import GitHubClient, GitHubError, inspect_action

CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
V7_0_0 = "9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0"
V4_4_0 = "11d5960a326750d5838078e36cf38b85af677262"
V4_2_2 = "11bd71901bbe5b1630ceea73d27597364c9af683"
PRE = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
UNRELEASED = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def _tag(name: str, sha: str) -> dict:
    return {"name": name, "commit": {"sha": sha}}


def _release(name: str, *, prerelease: bool = False, draft: bool = False) -> dict:
    return {"tag_name": name, "prerelease": prerelease, "draft": draft}


class FakeGitHub:
    def __init__(
        self,
        *,
        repo_status: int = 200,
        tags: list | None = None,
        releases: list | None = None,
        files: set[str] | None = None,
        commits: dict[str, str] | None = None,
        ambiguous: set[str] | None = None,
    ) -> None:
        self.repo_status = repo_status
        self.tags = tags if tags is not None else _checkout_tags()
        self.releases = releases if releases is not None else _checkout_releases()
        self.files = files
        self.commits = commits or {}
        self.ambiguous = ambiguous or set()

    def get(self, path: str, query: dict | None = None) -> tuple[int, object]:
        query = query or {}
        page = query.get("page", "1")
        if path.endswith("/tags"):
            return 200, self.tags if page == "1" else []
        if path.endswith("/releases"):
            return 200, self.releases if page == "1" else []
        if "/contents/" in path:
            if self.files is None:
                return 200, {"type": "file"}
            ref = query.get("ref", "default")
            if ref in self.files:
                return 200, {"type": "file"}
            return 404, {"message": "Not Found"}
        if "/commits/" in path:
            name = path.rsplit("/", 1)[-1]
            if name in self.ambiguous:
                return 422, {"message": "ambiguous"}
            if name in self.commits:
                return 200, {"sha": self.commits[name]}
            return 404, {"message": "Not Found"}
        if self.repo_status != 200:
            return self.repo_status, {"message": "Not Found"}
        return 200, {"default_branch": "main"}


def _checkout_tags() -> list[dict]:
    return [
        _tag("v7.0.3", UNRELEASED),
        _tag("v7.0.2", PRE),
        _tag("v7.0.1", CHECKOUT_SHA),
        _tag("v7", CHECKOUT_SHA),
        _tag("v7.0.0", V7_0_0),
        _tag("v4.4.0", V4_4_0),
        _tag("v4", V4_4_0),
        _tag("v4.2.2", V4_2_2),
    ]


def _checkout_releases() -> list[dict]:
    return [
        _release("v7.0.2", prerelease=True),
        _release("v7.0.1"),
        _release("v7.0.0"),
        _release("v4.4.0"),
        _release("v4.2.2"),
    ]


def _checkout() -> FakeGitHub:
    return FakeGitHub()


def test_latest_stable_checkout() -> None:
    text = inspect_action("actions/checkout", client=_checkout())
    assert "action: actions/checkout" in text
    assert "létezik: igen" in text
    assert "legfrissebb stabil: v7.0.1" in text
    assert "főverzió: v7" in text
    assert f"sha: {CHECKOUT_SHA}" in text
    assert f"pin: actions/checkout@{CHECKOUT_SHA} # v7.0.1" in text
    assert "v7.0.2" not in text
    assert "v7.0.3" not in text


def test_old_version_recommends_latest_and_same_major() -> None:
    text = inspect_action("uses: actions/checkout@v4.2.2", client=_checkout())
    assert "megadott: v4.2.2" in text
    assert f"megadott sha: {V4_2_2}" in text
    assert f"v4.2.2 régebbi. Erre érdemes frissíteni: v7.0.1 (sha: {CHECKOUT_SHA})." in text
    assert f"ugyanazon főverzió: v4.4.0 (sha: {V4_4_0})" in text


def test_version_without_v_resolves_sha() -> None:
    text = inspect_action("actions/checkout", "7.0.1", client=_checkout())
    assert "megadott: v7.0.1" in text
    assert f"megadott sha: {CHECKOUT_SHA}" in text
    assert "ez a legfrissebb stabil verzió." in text


def test_verzio_overrides_ref_in_action() -> None:
    text = inspect_action("actions/checkout@v4.2.2", "v7.0.1", client=_checkout())
    assert "megadott: v7.0.1" in text
    assert "régebbi" not in text


def test_moving_major_behind_latest() -> None:
    text = inspect_action("actions/checkout", "v4", client=_checkout())
    assert "megadott: v4" in text
    assert "pontos verzió: v4.4.0" in text
    assert f"megadott sha: {V4_4_0}" in text
    assert "v4.4.0 régebbi" in text
    assert "ugyanazon főverzió" not in text


def test_moving_major_tag_is_current() -> None:
    text = inspect_action("actions/checkout", "v7", client=_checkout())
    assert "megadott: v7" in text
    assert "pontos verzió: v7.0.1" in text
    assert f"megadott sha: {CHECKOUT_SHA}" in text
    assert "mozgó címke" in text
    assert "ez a legfrissebb stabil verzió." in text


def test_sha_resolves_to_version() -> None:
    text = inspect_action("actions/checkout", CHECKOUT_SHA, client=_checkout())
    assert f"megadott sha: {CHECKOUT_SHA}" in text
    assert "megadott verzió: v7.0.1" in text
    assert "ez a legfrissebb stabil verzió." in text


def test_old_sha_recommends_update() -> None:
    text = inspect_action(f"actions/checkout@{V4_2_2}", client=_checkout())
    assert f"megadott sha: {V4_2_2}" in text
    assert "megadott verzió: v4.2.2" in text
    assert f"ugyanazon főverzió: v4.4.0 (sha: {V4_4_0})" in text
    assert CHECKOUT_SHA in text


def test_short_sha_expands() -> None:
    client = _checkout()
    client.commits["3d3c42e"] = CHECKOUT_SHA
    text = inspect_action("actions/checkout", "3d3c42e", client=client)
    assert f"megadott sha: {CHECKOUT_SHA}" in text
    assert "megadott verzió: v7.0.1" in text


def test_ambiguous_sha() -> None:
    client = _checkout()
    client.ambiguous.add("abc1234")
    text = inspect_action("actions/checkout", "abc1234", client=client)
    assert "több commitra illik" in text


def test_untagged_commit_still_recommends_latest() -> None:
    sha = "cccccccccccccccccccccccccccccccccccccccc"
    client = _checkout()
    client.commits[sha] = sha
    text = inspect_action("actions/checkout", sha, client=client)
    assert "megadott verzió: nincs hozzá címke" in text
    assert f"erre érdemes frissíteni: v7.0.1 (sha: {CHECKOUT_SHA})" in text


def test_missing_version_recommends_latest() -> None:
    text = inspect_action("actions/checkout", "v9.9.9", client=_checkout())
    assert "A megadott verzió nem létezik: v9.9.9" in text
    assert f"erre érdemes frissíteni: v7.0.1 (sha: {CHECKOUT_SHA})" in text


def test_branch_is_not_a_release() -> None:
    client = _checkout()
    client.commits["main"] = "dddddddddddddddddddddddddddddddddddddddd"
    text = inspect_action("actions/checkout", "main", client=client)
    assert "a main ág, nem kiadás" in text
    assert "v7.0.1" in text


def test_missing_repo() -> None:
    text = inspect_action("actions/nincs-ilyen", client=FakeGitHub(repo_status=404))
    assert "létezik: nem" in text
    assert "A GitHubon nincs ilyen repó." in text


def test_repo_without_action_file() -> None:
    text = inspect_action("actions/checkout", client=FakeGitHub(files=set()))
    assert "létezik: nem" in text
    assert "action.yml" in text


def test_skips_release_without_action_file() -> None:
    text = inspect_action(
        "actions/checkout",
        client=FakeGitHub(files={"v7.0.0", "v4.4.0", "v4.2.2", "default"}),
    )
    assert "legfrissebb stabil: v7.0.0" in text
    assert f"sha: {V7_0_0}" in text
    assert "kihagyva: v7.0.1" in text


def test_release_missing_from_tags_uses_commit() -> None:
    sha = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    text = inspect_action(
        "acme/action",
        client=FakeGitHub(
            tags=[_tag("v1.0.0", V4_2_2)],
            releases=[_release("v1.2.0"), _release("v1.0.0")],
            commits={"v1.2.0": sha},
        ),
    )
    assert "legfrissebb stabil: v1.2.0" in text
    assert f"sha: {sha}" in text


def test_draft_release_is_skipped() -> None:
    text = inspect_action(
        "acme/action",
        client=FakeGitHub(
            tags=[_tag("v2.0.0", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"), _tag("v1.0.0", V4_2_2)],
            releases=[_release("v2.0.0", draft=True), _release("v1.0.0")],
        ),
    )
    assert "legfrissebb stabil: v1.0.0" in text


def test_tags_only_when_there_is_no_release() -> None:
    text = inspect_action(
        "acme/action",
        client=FakeGitHub(
            tags=[_tag("v1.2.0", CHECKOUT_SHA), _tag("v1.1.0", V4_2_2)],
            releases=[],
        ),
    )
    assert "legfrissebb stabil: v1.2.0" in text
    assert f"sha: {CHECKOUT_SHA}" in text


def test_major_tags_when_there_is_no_patch_release() -> None:
    text = inspect_action(
        "acme/action",
        client=FakeGitHub(
            tags=[_tag("v2", CHECKOUT_SHA), _tag("v1", V4_2_2)],
            releases=[_release("v2"), _release("v1")],
        ),
    )
    assert "legfrissebb stabil: v2" in text
    assert f"sha: {CHECKOUT_SHA}" in text


def test_subpath_action() -> None:
    text = inspect_action("github/codeql-action/init", client=_checkout())
    assert text.startswith("action: github/codeql-action/init\n")
    assert f"pin: github/codeql-action/init@{CHECKOUT_SHA} # v7.0.1" in text


def test_invalid_action_does_not_call_github() -> None:
    class Exploding:
        def get(self, path: str, query: dict | None = None) -> tuple[int, object]:
            raise AssertionError(path)

    assert inspect_action("checkout", client=Exploding()).startswith("Érvénytelen")


def test_rate_limit() -> None:
    class Limited:
        def get(self, path: str, query: dict | None = None) -> tuple[int, object]:
            return 403, {"message": "API rate limit exceeded"}

    text = inspect_action("actions/checkout", client=Limited())
    assert "limitje betelt" in text


def test_client_sends_token(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str | None] = {}

    class Response:
        status = 200

        def read(self) -> bytes:
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> bool:
            return False

    def fake_urlopen(request, timeout: int):  # type: ignore[no-untyped-def]
        seen["auth"] = request.get_header("Authorization")
        seen["url"] = request.full_url
        assert timeout == 15
        return Response()

    monkeypatch.setattr("fejlett_mcp_szerver.tools.github_action.urlopen", fake_urlopen)
    status, body = GitHubClient("secret").get("/repos/a/b", {"page": "1"})
    assert status == 200
    assert body == {}
    assert seen["auth"] == "Bearer secret"
    assert seen["url"] == "https://api.github.com/repos/a/b?page=1"


def test_client_reads_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout: int):  # type: ignore[no-untyped-def]
        raise HTTPError(
            request.full_url,
            404,
            "Not Found",
            EmailMessage(),
            BytesIO(b'{"message":"Not Found"}'),
        )

    monkeypatch.setattr("fejlett_mcp_szerver.tools.github_action.urlopen", fake_urlopen)
    status, body = GitHubClient().get("/repos/a/b")
    assert status == 404
    assert body == {"message": "Not Found"}


def test_from_env_prefers_personal_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "pat")
    monkeypatch.setenv("GITHUB_TOKEN", "gha")
    assert GitHubClient.from_env()._token == "pat"


def test_client_network_error_is_a_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout: int):  # type: ignore[no-untyped-def]
        raise TimeoutError("timed out")

    monkeypatch.setattr("fejlett_mcp_szerver.tools.github_action.urlopen", fake_urlopen)
    text = inspect_action("actions/checkout")
    assert "nem elérhető" in text
    assert "timed out" in text


def test_client_rejects_non_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status = 200

        def read(self) -> bytes:
            return b"not-json"

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> bool:
            return False

    monkeypatch.setattr(
        "fejlett_mcp_szerver.tools.github_action.urlopen",
        lambda request, timeout: Response(),
    )
    with pytest.raises(GitHubError, match="nem JSON"):
        GitHubClient().get("/repos/a/b")
