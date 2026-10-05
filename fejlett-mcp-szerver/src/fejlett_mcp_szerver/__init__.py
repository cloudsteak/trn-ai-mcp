"""A src/fejlett_mcp_szerver csomag.

Az első MCP szerverben minden a server.py-ban volt. Itt a server.py
hoz létre az MCPServert, a képességek külön fájlban vannak, és az
externals.py külső MCP-ket is csatol. A __init__.py teszi a mappát csomaggá.
Protokoll: 2026-07-28.
"""

from pathlib import Path

__version__ = "0.1.0"
PROTOCOL_VERSION = "2026-07-28"

# src/fejlett_mcp_szerver/__init__.py: a projekt gyökere két szinttel feljebb van.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
