"""Aktuális dátum és idő egy IANA időzónában."""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)


def register(mcp: MCPServer) -> None:
    @mcp.tool(title="Jelenlegi idő")
    def aktualis_ido(timezone: str = "Europe/Budapest") -> str:
        """Visszaadja a jelenlegi dátumot és időt egy IANA időzónában.

        Akkor hívd, ha a felhasználó azt kérdezi, hány óra van, mennyi az idő.

        Args:
            timezone: IANA időzóna, például Europe/Budapest vagy UTC.
        """
        logger.info("aktualis_ido timezone=%s", timezone)
        try:
            tz = ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            return f"Ismeretlen időzóna: {timezone}. IANA nevet használj, pl. Europe/Budapest."
        return datetime.now(tz).isoformat()
