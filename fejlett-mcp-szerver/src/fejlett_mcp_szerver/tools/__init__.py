"""A tools mappa a saját toolokat tartalmazza, mindegyik külön fájlban.

A Python a mappát csak __init__.py-jal kezeli csomagként, ezért tudja
a server.py importálni a register_tools függvényt.
Ez a fájl sorolja fel a toolokat. Új tool: import, és egy sor a _TOOLS-ba.
"""

from mcp.server.mcpserver import MCPServer

from fejlett_mcp_szerver.tools import (
    aktualis_ido,
    idokulonbseg,
    jelszo,
    osszead,
    qr_kod,
    uticel,
    weboldal_osszefoglalo,
)

_TOOLS = (
    osszead,
    aktualis_ido,
    weboldal_osszefoglalo,
    qr_kod,
    idokulonbseg,
    jelszo,
    uticel,
)


def register_tools(mcp: MCPServer) -> None:
    for tool in _TOOLS:
        tool.register(mcp)
