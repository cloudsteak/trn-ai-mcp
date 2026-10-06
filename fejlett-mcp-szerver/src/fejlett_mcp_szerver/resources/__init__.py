"""A resources mappa a saját resource-okat tartalmazza, mindegyik külön fájlban.

A Python a mappát csak __init__.py-jal kezeli csomagként, ezért tudja
a server.py importálni a register_resources függvényt.
Ez a fájl sorolja fel a resource-okat. Új resource: import, és egy sor a _RESOURCES-ba.
"""

from mcp.server.mcpserver import MCPServer

from fejlett_mcp_szerver.resources import ability_list, utazas_adatok

_RESOURCES = (
    utazas_adatok,
    ability_list,
)


def register_resources(mcp: MCPServer) -> None:
    for resource in _RESOURCES:
        resource.register(mcp)
