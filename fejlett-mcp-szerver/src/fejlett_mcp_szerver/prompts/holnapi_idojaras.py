"""Indító üzenet a holnapi időjáráshoz."""

from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)


def register(mcp: MCPServer) -> None:
    @mcp.prompt(title="Holnapi időjárás (prompt)")
    def holnapi_idojaras(hely: str = "Budapest") -> str:
        """Indító üzenet: a modell megmondja a holnapi időjárást.

        A felhasználó választja ki a kliens prompt listájából.

        Args:
            hely: Város vagy hely, például Budapest. Alapértelmezett: Budapest.
        """
        logger.info("holnapi_idojaras hely=%s", hely)
        return (
            "Mondd meg a holnapi időjárást. Először a hely_kereses toolt hívd a koordinátákért, "
            "utána az elorejelzes toolt. Ne emlékezetből válaszolj.\n\n"
            f"Hely: {hely}"
        )
