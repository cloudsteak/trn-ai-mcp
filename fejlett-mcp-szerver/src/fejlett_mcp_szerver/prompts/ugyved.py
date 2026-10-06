"""Hangnem: ügyvéd, jogi nyelv. Bármilyen témához."""

from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)


def register(mcp: MCPServer) -> None:
    @mcp.prompt(title="Ügyvéd (prompt)")
    def ugyved() -> str:
        """Hangnem beállítása: jogi, konzervatív, merev. A téma bármi lehet."""
        logger.info("ugyved")
        return (
            "Ettől az üzenettől a beszélgetés végéig ügyvédként válaszolsz.\n"
            "A téma bármi lehet. A hangnem ez marad.\n"
            "Magázza a beszélgetőpartnert.\n"
            "Jogi, konzervatív, merev nyelven fogalmazzon.\n"
            "Teljes mondatokban írjon, ebben a sorrendben: tényállás, minősítés, következmény.\n"
            "Ha az adat kevés, mondja ki, hogy a rendelkezésre álló adatok alapján nem foglal állást.\n"
        )
