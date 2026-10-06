"""Hangnem: alfa generációs szleng. Bármilyen témához."""

from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)


def register(mcp: MCPServer) -> None:
    @mcp.prompt(title="Alfa (prompt)")
    def alfa() -> str:
        """Hangnem beállítása: alfa generációs szleng. A téma bármi lehet."""
        logger.info("alfa")
        return (
            "Ettől az üzenettől a beszélgetés végéig alfa generációs szlengben beszélsz.\n"
            "A téma bármi lehet. A hangnem ez marad.\n"
            "Tegezz, röviden, mintha chatben írnál.\n"
            "Használd ezeket a szavakat: no cap, slay, aura, mid, W, L, NPC, sigma, alap, random, cringe, tesó.\n"
            "A válasz tartalma maradjon pontos, csak a hangnem legyen ez.\n"
        )
