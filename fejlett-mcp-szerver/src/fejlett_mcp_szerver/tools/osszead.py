"""Két szám összeadása."""

from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)


def register(mcp: MCPServer) -> None:
    @mcp.tool(title="Összeadás")
    def osszead(a: float, b: float) -> float:
        """Két számot ad össze. Minden összeadásnál ezt hívd (összead, plusz)."""
        logger.info("osszead a=%s b=%s", a, b)
        return a + b
