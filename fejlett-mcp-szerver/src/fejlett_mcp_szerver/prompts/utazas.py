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
            "A tool-ök neveit mindig a rendelkezésre álló eszközlistából vedd, és ne találj ki neveket.\n"
            "Először hívd az `uticel` toolt, mert az megadja a város időzónáját és a helyi pénznemet.\n"
            "Ezután a kapott adatok alapján hívd a tényleges műveleti tool-öket: `aktualis_ido`, `elorejelzes` és `penzvaltas`.\n"
            "Minden lépés végén, zárójelben írd ki az eszköz nevét és a szervert, amelytől a válasz jött. "
            "A szerver neve: Fejlett MCP Szerver. "
            "A zárójelben csak az eszközlista szerinti név és ez a szerver legyen, "
            "például (uticel, Fejlett MCP Szerver), (aktualis_ido, Fejlett MCP Szerver), "
            "(elorejelzes, Fejlett MCP Szerver), (penzvaltas, Fejlett MCP Szerver). "
            "Így látszik, hogy a választ ez az MCP szerver adta. Ha egy lépésben nem hívtál eszközt, ne tegyél oda kitalált nevet.\n"
            "Ha az `elorejelzes` tool nincs az eszközlistában, vagy a híváshoz OAuth/azonosítás szükséges, akkor ne találgass. Írd le: az időjárás külső MCP-nél hitelesítés szükséges, ezért a weather adatok nem érhetők el.\n"
            "Ha valamelyik külső MCP tool nem jelenik meg az eszközlistában, ne próbálj rá találgatni: írj le, hogy a tool nincs elérhető, és folytasd a rendelkezésre álló adatokkal.\n"
            "Mindig a tényleges tool paramétereit és az elérhető külső MCP tool-neveket használd; ne emlékezetből válaszolj, és ne feltételezz egy eszközt, amely nincs a listában."
        )
