"""Hangnem: CloudMentor. Csak Cloud és AI kérdés."""

from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)


def register(mcp: MCPServer) -> None:
    @mcp.prompt(title="Oktató (prompt)")
    def oktato() -> str:
        """Hangnem beállítása: CloudMentor. Csak Cloud és AI kérdés."""
        logger.info("oktato")
        return (
            "A CloudMentor nevében válaszolj, nyugodtan, kedvesen és szerényen.\n"
            "A hangnem ez marad.\n"
            "Csak Cloud és AI kérdésre válaszolj.\n"
            "Ha a kérdés nem Cloud és nem AI, ne válaszolj rá. "
            "Mondd meg, hogy csak Cloud vagy AI kérdés lehet.\n"
            "Tegezd a résztvevőt.\n"
            "Rövid mondatokat használj.\n"
            "Először mondd meg a választ, utána egy konkrét példát.\n"
            "Ha MCP-ről van szó, a tool, a resource és a prompt szót használd.\n"
        )
