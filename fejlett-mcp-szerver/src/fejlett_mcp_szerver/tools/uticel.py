"""Úti cél: időzóna és helyi pénznem egy városhoz."""

from __future__ import annotations

import logging
import unicodedata

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)

# Néhány gyakori úti cél. A kulcs a város ékezet nélküli neve.
_CELOK = (
    {"varos": "Cancun", "orszag": "Mexikó", "idozona": "America/Cancun", "penznem": "MXN"},
    {"varos": "Budapest", "orszag": "Magyarország", "idozona": "Europe/Budapest", "penznem": "HUF"},
    {"varos": "Bécs", "orszag": "Ausztria", "idozona": "Europe/Vienna", "penznem": "EUR"},
    {"varos": "Prága", "orszag": "Csehország", "idozona": "Europe/Prague", "penznem": "CZK"},
    {"varos": "London", "orszag": "Egyesült Királyság", "idozona": "Europe/London", "penznem": "GBP"},
    {"varos": "Párizs", "orszag": "Franciaország", "idozona": "Europe/Paris", "penznem": "EUR"},
    {"varos": "Róma", "orszag": "Olaszország", "idozona": "Europe/Rome", "penznem": "EUR"},
    {"varos": "Barcelona", "orszag": "Spanyolország", "idozona": "Europe/Madrid", "penznem": "EUR"},
    {"varos": "New York", "orszag": "Egyesült Államok", "idozona": "America/New_York", "penznem": "USD"},
    {"varos": "Tokió", "orszag": "Japán", "idozona": "Asia/Tokyo", "penznem": "JPY"},
    {"varos": "Dubai", "orszag": "Egyesült Arab Emírségek", "idozona": "Asia/Dubai", "penznem": "AED"},
)


def _fold(value: str) -> str:
    stripped = unicodedata.normalize("NFD", value.strip().casefold())
    return "".join(char for char in stripped if not unicodedata.combining(char))


def lookup(varos: str, orszag: str) -> str:
    city = _fold(varos)
    country = _fold(orszag)
    for cel in _CELOK:
        if _fold(cel["varos"]) == city and _fold(cel["orszag"]) == country:
            return (
                f"város: {cel['varos']}\n"
                f"ország: {cel['orszag']}\n"
                f"időzóna: {cel['idozona']}\n"
                f"pénznem: {cel['penznem']}"
            )
    return (
        f"Nincs adat erről a városról: {varos}, {orszag}. "
        "A listában lévő várost adj meg, például Cancun, Mexikó."
    )


def register(mcp: MCPServer) -> None:
    @mcp.tool(title="Úti cél")
    def uticel(varos: str = "Cancun", orszag: str = "Mexikó") -> str:
        """Egy város időzónáját és az ország pénznemét adja vissza.

        Utazás előtt ezt hívd. Az időt és az árfolyamot utána kérdezd,
        az itt kapott időzónával és pénznemmel.

        Args:
            varos: A város. Alapértelmezett: Cancun.
            orszag: Az ország. Alapértelmezett: Mexikó.
        """
        logger.info("uticel varos=%s orszag=%s", varos, orszag)
        return lookup(varos, orszag)
