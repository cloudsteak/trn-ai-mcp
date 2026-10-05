"""A prompts mappa a saját promptokat tartalmazza, mindegyik külön fájlban.

A Python a mappát csak __init__.py-jal kezeli csomagként, ezért tudja
a server.py importálni a register_prompts függvényt.
Ez a fájl sorolja fel a promptokat. Új prompt: import, és egy sor a _PROMPTS-ba.
"""

from mcp.server.mcpserver import MCPServer

from fejlett_mcp_szerver.prompts import alfa, holnapi_idojaras, oktato, ugyved, utazas

_PROMPTS = (
    oktato,
    alfa,
    ugyved,
    utazas,
    holnapi_idojaras,
)


def register_prompts(mcp: MCPServer) -> None:
    for prompt in _PROMPTS:
        prompt.register(mcp)
