"""Indító üzenet egy városba utazás előkészítéséhez."""

from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)


def register(mcp: MCPServer) -> None:
    @mcp.prompt(title="Utazás (prompt)")
    def utazas(
        varos: str = "Cancun",
        orszag: str = "Mexikó",
        osszeg: int = 1000000,
        penznem: str = "HUF",
    ) -> str:
        """Indító üzenet: idő, időjárás és pénzváltás egy városban.

        A felhasználó választja ki a kliens prompt listájából.

        Args:
            varos: A város. Alapértelmezett: Cancun.
            orszag: Az ország. Alapértelmezett: Mexikó.
            osszeg: Ennyi pénzt vigyen. Alapértelmezett: 1000000.
            penznem: A magaddal vitt pénz pénzneme. Alapértelmezett: HUF.
        """
        logger.info("utazas varos=%s orszag=%s osszeg=%s %s", varos, orszag, osszeg, penznem)
        return (
            f"Ide utazom: {varos}, {orszag}. Viszek {osszeg} {penznem} összeget.\n"
            "Mondd meg, mennyi ott az idő most.\n"
            "Mondd meg az időjárást.\n"
            "Váltsd át az összeget az ország fizetőeszközére.\n"
            "Először az uticel toolt hívd: az adja az időzónát és a pénznemet. "
            "Azzal hívd az aktualis_ido, az elorejelzes és a penzvaltas toolt. "
            "Ne emlékezetből válaszolj."
        )
