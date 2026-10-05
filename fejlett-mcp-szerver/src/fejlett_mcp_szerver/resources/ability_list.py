"""Csoportosított lista a szerver képességeiről."""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from fejlett_mcp_szerver import PROJECT_ROOT
from fejlett_mcp_szerver.prompts import _PROMPTS
from fejlett_mcp_szerver.tools import _TOOLS

_RESOURCES = (
    "utazas://adatok",
    "training://ability-list",
)


_PROMPT_LABELS = {
    "oktato": "Oktató (prompt)",
    "alfa": "Alfa (prompt)",
    "ugyved": "Ügyvéd (prompt)",
    "utazas": "Utazás (prompt)",
    "holnapi_idojaras": "Holnapi időjárás (prompt)",
}


def _names(modules: tuple) -> list[str]:
    return [module.__name__.rsplit(".", 1)[-1] for module in modules]


def _prompt_labels(modules: tuple) -> list[str]:
    return [_PROMPT_LABELS[name] for name in _names(modules)]


def _external_tool_names() -> list[str]:
    path = PROJECT_ROOT / "externals.json"
    if not path.is_file():
        return []
    names: list[str] = []
    for item in json.loads(path.read_text()):
        rename = item.get("rename") or {}
        if rename:
            names.extend(rename.values())
            continue
        names.extend(item.get("only") or ())
    return names


def _section(title: str, lines: list[str]) -> str:
    body = "\n".join(f"- {line}" for line in lines) if lines else "- (nincs)"
    return f"{title}:\n{body}"


def register(mcp: MCPServer) -> None:
    @mcp.resource("training://ability-list")
    def ability_list() -> str:
        """Toolok, resource-ok, promptok és külső toolok, csoportonként."""
        return "\n\n".join(
            (
                _section("toolok", _names(_TOOLS)),
                _section("resource-ok", list(_RESOURCES)),
                _section("promptok", _prompt_labels(_PROMPTS)),
                _section("külső toolok", _external_tool_names()),
            )
        )
