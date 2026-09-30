# Szükséges Python csomagok importálása
from mcp.server.mcpserver import MCPServer

# MCP szerver példány létrehozása
mcp = MCPServer("Első MCP Szerverem")


# Első eszköz (tool) létrehozása: Összeadás
@mcp.tool(name="Osszeadas", description="Két szám összeadására szolgáló eszköz")
def osszeadas(a: int, b: int) -> int:
    """A két számot összeadja és a végeredményt adja vissza."""
    return a + b


# A fő program indítása - entry point
if __name__ == "__main__":
    print(f"{mcp.name} indul...")
    # A szerver futtatása a helyi gépen a 8000-es porton
    mcp.run(host="0.0.0.0", port=8000)
