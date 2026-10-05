"""Más MCP szervereket csatol ehhez.

Ez a folyamat MCP szerver a Claude Desktop felé, és MCP kliens
az externals.json minden eleméhez (stdio parancs vagy HTTP URL).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client
from mcp.server.mcpserver import MCPServer
from mcp.server.subscriptions import ToolsListChanged
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.types import CallToolResult, TextContent

from fejlett_mcp_szerver import PROJECT_ROOT

logger = logging.getLogger(__name__)

# Egy külső MCP ennyit kaphat a háttérben. A szerver addig nem vár.
_EXTERNAL_TIMEOUT_S = 12
_CLOSE_TIMEOUT_S = 2
_NAME_SAFE = re.compile(r"[^A-Za-z0-9_]")


@dataclass(frozen=True)
class ExternalSpec:
    name: str
    command: str | None = None
    args: tuple[str, ...] = ()
    url: str | None = None
    env: dict[str, str] | None = None
    rename: dict[str, str] = field(default_factory=dict)
    require_env: tuple[str, ...] = ()
    only: tuple[str, ...] = ()
    headers: dict[str, str] = field(default_factory=dict)


class _Passthrough:
    """Accept the other MCP's arguments without re-validating our wrapper."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.output_schema = inner.output_schema

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return arguments

    async def call_fn(
        self,
        fn: Any,
        fn_is_async: bool,
        arguments: dict[str, Any],
        arguments_to_pass_directly: dict[str, Any] | None = None,
    ) -> Any:
        kwargs = dict(arguments)
        if arguments_to_pass_directly:
            kwargs.update(arguments_to_pass_directly)
        return await fn(**kwargs)

    def convert_result(self, result: Any) -> Any:
        return self._inner.convert_result(result)


def _load_dotenv() -> None:
    env_file = PROJECT_ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _expand(value: str | None) -> str | None:
    if not value:
        return value
    return os.path.expandvars(value)


def load_externals(path: Path | None = None) -> list[ExternalSpec]:
    _load_dotenv()
    raw = os.getenv("MCP_EXTERNALS", "externals.json")
    if raw in {"", "off", "none"}:
        return []
    config = path or Path(raw)
    if not config.is_absolute():
        config = PROJECT_ROOT / config
    if not config.is_file():
        logger.warning("External MCP config not found: %s", config)
        return []
    data = json.loads(config.read_text())
    specs: list[ExternalSpec] = []
    for item in data:
        missing = [key for key in (item.get("require_env") or ()) if not os.getenv(key)]
        if missing:
            logger.warning(
                "External MCP %s: missing %s — skipped", item["name"], ", ".join(missing)
            )
            continue
        url = _expand(item.get("url"))
        if item.get("url") and url and "$" in url:
            logger.warning(
                "External MCP %s: URL has an unset $VAR — skipped", item["name"]
            )
            continue
        extra_env = item.get("env") or {}
        headers = item.get("headers") or {}
        specs.append(
            ExternalSpec(
                name=item["name"],
                command=item.get("command"),
                args=tuple(item.get("args") or ()),
                url=url,
                env={key: _expand(value) or "" for key, value in extra_env.items()},
                rename=item.get("rename") or {},
                require_env=tuple(item.get("require_env") or ()),
                only=tuple(item.get("only") or ()),
                headers={key: _expand(value) or "" for key, value in headers.items()},
            )
        )
    return specs


def expand_process_path() -> None:
    """Claude Desktop often starts us with a tiny PATH. Put Homebrew and nvm on it."""
    extras = ["/opt/homebrew/bin", "/usr/local/bin"]
    nvm_nodes = Path.home() / ".nvm/versions/node"
    if nvm_nodes.is_dir():
        extras.extend(str(path / "bin") for path in sorted(nvm_nodes.iterdir()) if (path / "bin").is_dir())
    os.environ["PATH"] = os.pathsep.join([*extras, os.environ.get("PATH", "")])


@asynccontextmanager
async def _http_client(url: str, headers: dict[str, str] | None):
    if headers:
        async with create_mcp_http_client(headers=headers) as http:
            async with streamable_http_client(url, http_client=http) as streams:
                yield streams
        return
    async with streamable_http_client(url) as streams:
        yield streams


def _client_target(spec: ExternalSpec):
    if spec.url:
        return _http_client(spec.url, spec.headers or None)
    if not spec.command:
        raise ValueError(f"External MCP {spec.name!r} needs command or url")
    expand_process_path()
    command = shutil.which(spec.command) or spec.command
    return StdioServerParameters(
        command=command,
        args=list(spec.args),
        env={**os.environ, **(spec.env or {})},
        cwd=str(PROJECT_ROOT),
    )


_TITLES = {
    "penzvaltas": "Pénzváltás",
    "elorejelzes": "Előrejelzés",
    "riasztasok": "Riasztások",
    "levegominoseg": "Levegőminőség",
    "github_profil": "GitHub profil",
    "repo_kereses": "Repókeresés",
    "fajl_tartalom": "Fájl tartalma",
    "issue_lista": "Issue-k listája",
    "pr_lista": "PR-ok listája",
    "issue_kereses": "Issue keresés",
    "pr_kereses": "PR keresés",
}

_DESCRIPTIONS = {
    "penzvaltas": "Pénzt vált vagy árfolyamot ad (EUR, HUF, USD).",
    "elorejelzes": "Időjárás és előrejelzés egy helyre.",
    "riasztasok": "Időjárási riasztások (főleg USA).",
    "levegominoseg": "Levegőminőség, AQI.",
    "github_profil": "A bejelentkezett GitHub felhasználó adatai.",
    "repo_kereses": "GitHub repók keresése.",
    "fajl_tartalom": "Fájl vagy mappa tartalma egy GitHub repóban.",
    "issue_lista": "Issue-k egy adott GitHub repóban.",
    "pr_lista": "Pull requestek egy adott GitHub repóban.",
    "issue_kereses": "Issue-k keresése, akár egy egész szervezetben (org:NÉV is:open).",
    "pr_kereses": "PR-ok keresése, akár egy egész szervezetben (org:NÉV is:open).",
}


def _human_title(name: str) -> str:
    return _TITLES.get(name, name.replace("_", " ").capitalize())


def _exposed_name(
    server: MCPServer,
    prefix: str,
    tool_name: str,
    rename: dict[str, str] | None = None,
) -> str:
    wanted = (rename or {}).get(tool_name, tool_name)
    taken = {item.name for item in server._tool_manager.list_tools()}
    if wanted not in taken:
        return wanted
    return f"{_NAME_SAFE.sub('_', prefix)}_{wanted}"


def _make_forwarder(client: Client, prefix: str, original: str):
    async def forward(**arguments: Any) -> str:
        result = await client.call_tool(original, arguments)
        logger.info("external %s.%s", prefix, original)
        return _result_text(result)

    return forward


def _result_text(result: CallToolResult) -> str:
    if result.structured_content is not None:
        return json.dumps(result.structured_content, ensure_ascii=False)
    parts = [block.text for block in result.content if isinstance(block, TextContent)]
    text = "\n".join(parts)
    if result.is_error and not text:
        return "A külső MCP tool hibát adott."
    return text


async def mount_client_tools(
    server: MCPServer,
    client: Client,
    prefix: str,
    rename: dict[str, str] | None = None,
    only: tuple[str, ...] | list[str] | None = None,
) -> list[str]:
    """Re-export tools from an already-connected MCP client."""
    mounted: list[str] = []
    allowed = set(only or ())
    listed = await client.list_tools()
    for tool in listed.tools:
        if allowed and tool.name not in allowed:
            continue
        exposed = _exposed_name(server, prefix, tool.name, rename)
        forward = _make_forwarder(client, prefix, tool.name)
        created = server._tool_manager.add_tool(
            forward,
            name=exposed,
            title=_human_title(exposed),
            description=_DESCRIPTIONS.get(
                exposed, tool.description or f"Külső MCP: {prefix}:{tool.name}"
            ),
            structured_output=False,
        )
        created.fn_metadata = _Passthrough(created.fn_metadata)
        if tool.input_schema:
            created.parameters = dict(tool.input_schema)
        mounted.append(exposed)
        logger.info("mounted external tool %s -> %s", tool.name, exposed)
    return mounted


async def _connect_external(
    server: MCPServer,
    spec: ExternalSpec,
    clients: dict[str, Client],
) -> Client | None:
    client = Client(_client_target(spec))
    try:
        async with asyncio.timeout(_EXTERNAL_TIMEOUT_S):
            await client.__aenter__()
            await mount_client_tools(server, client, spec.name, spec.rename, spec.only)
            clients[spec.name] = client
            return client
    except TimeoutError:
        logger.warning(
            "External MCP %s: no answer in %ss — skipped", spec.name, _EXTERNAL_TIMEOUT_S
        )
    except asyncio.CancelledError:
        await _close_client(client)
        raise
    except Exception:
        logger.exception("Could not connect external MCP %s", spec.name)
    await _close_client(client)
    return None


async def _close_client(client: Client) -> None:
    try:
        async with asyncio.timeout(_CLOSE_TIMEOUT_S):
            await client.__aexit__(None, None, None)
    except Exception:
        logger.warning("External MCP client did not close in time")


async def _connect_all(
    server: MCPServer,
    clients: dict[str, Client],
    opened: list[Client],
) -> None:
    results = await asyncio.gather(
        *(_connect_external(server, spec, clients) for spec in load_externals())
    )
    opened.extend(client for client in results if client is not None)
    if opened:
        await server._subscriptions.publish(ToolsListChanged())


@asynccontextmanager
async def external_lifespan(server: MCPServer) -> AsyncIterator[dict[str, Client]]:
    # A lifespan közben a kliens nem kap választ. A külső MCP-k ezért háttérben indulnak.
    clients: dict[str, Client] = {}
    opened: list[Client] = []
    task = asyncio.create_task(_connect_all(server, clients, opened))
    try:
        yield clients
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await asyncio.gather(*(_close_client(client) for client in opened))
