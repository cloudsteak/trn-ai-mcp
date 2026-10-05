"""Publikus weboldal összefoglalója a nyitóoldal HTML-je alapján."""

from __future__ import annotations

import logging
import re
from html import unescape
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)

_SKIP_TAGS = frozenset({"script", "style", "noscript", "svg", "template"})
_MAX_BYTES = 1_000_000
_TIMEOUT_S = 10


class _LandingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_title = False
        self._in_head = False
        self._skip = 0
        self.title_parts: list[str] = []
        self.meta: dict[str, str] = {}
        self.body_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: (value or "") for key, value in attrs}
        if tag == "head":
            self._in_head = True
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (attr.get("name") or attr.get("property") or "").lower()
            content = unescape(attr.get("content", "")).strip()
            if name and content:
                self.meta[name] = content
        if tag in _SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "head":
            self._in_head = False
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        text = unescape(data).strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        elif not self._in_head and self._skip == 0:
            self.body_parts.append(text)


def normalize_url(url: str) -> str:
    text = url.strip()
    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("http(s) webcímet adj meg, például https://example.com")
    return text


def fetch_landing(url: str) -> str:
    request = Request(url, headers={"User-Agent": "fejlett-mcp-szerver/0.1"})
    with urlopen(request, timeout=_TIMEOUT_S) as response:
        raw = response.read(_MAX_BYTES)
    return raw.decode("utf-8", errors="replace")


def summarize_html(html: str, url: str) -> str:
    parser = _LandingParser()
    parser.feed(html)
    parser.close()

    title = " ".join(parser.title_parts).strip() or parser.meta.get("og:title", "")
    description = (
        parser.meta.get("og:description")
        or parser.meta.get("description")
        or parser.meta.get("twitter:description")
        or ""
    )
    body = re.sub(r"\s+", " ", " ".join(parser.body_parts)).strip()
    if len(body) > 600:
        body = body[:600].rsplit(" ", 1)[0] + "…"

    lines = [f"url: {url}"]
    if title:
        lines.append(f"cím: {title}")
    if description:
        lines.append(f"összefoglaló: {description}")
    elif body:
        lines.append(f"összefoglaló: {body}")
    else:
        lines.append("összefoglaló: A nyitóoldalon alig van olvasható szöveg.")
    if description and body:
        lines.append(f"részlet: {body}")
    return "\n".join(lines)


def register(mcp: MCPServer) -> None:
    @mcp.tool(title="Weboldal összefoglaló")
    def weboldal_osszefoglalo(url: str) -> str:
        """Összefoglal egy weboldalt a nyitóoldal alapján (cím, leírás, első szöveg).

        Akkor hívd, ha a felhasználó URL-t ad, vagy azt kérdezi, miről szól az oldal.

        Args:
            url: Webcím, https:// nélkül is lehet.
        """
        logger.info("weboldal_osszefoglalo url=%s", url)
        try:
            target = normalize_url(url)
            return summarize_html(fetch_landing(target), target)
        except (ValueError, URLError, TimeoutError, OSError) as exc:
            return f"A nyitóoldalt nem sikerült beolvasni: {exc}"
