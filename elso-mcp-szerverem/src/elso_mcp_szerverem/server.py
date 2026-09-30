# Szükséges Python csomagok importálása
from mcp.server.mcpserver import MCPServer

# MCP szerver példány létrehozása
mcp = MCPServer("Első MCP Szerverem")

# A fő program indítása - entry point
if __name__ == "__main__":
    print(f"{mcp.name} indul...")
    # A szerver futtatása a helyi gépen a 8000-es porton
    mcp.run(host="0.0.0.0", port=8000)
