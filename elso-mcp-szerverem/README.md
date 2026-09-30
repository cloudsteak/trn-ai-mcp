# Első MCP szerverem

Ez egy alap MCP szerver. A hivatalos leírás: [MCP 2026-07-28](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro). A Python SDK első lépései: [first steps](https://py.sdk.modelcontextprotocol.io/get-started/first-steps/).

MCP verzió: `2026-07-28`.

A projektben az MCPServer-t (a FastMCP hivatalos, 2.x.x verziós utódját) használjuk.
Ennek előnye, hogy a protokoll-kódok és JSON sémák manuális definíciója helyett Python dekorátorokkal (annotation) hozhatjuk létre az AI eszközöket. Emellett a keretrendszer a háttérben automatikusan kezeli a beépített hibakeresést, valamint az állapotmentes (stateless) kommunikációs protokoll szabályait.
Ezzel sokkal gyorsabban és rövidebben tudjuk ugyanazt a funkcionalitást megvalósítani.

## Mappastruktúra

```plaintext
elso-mcp-szerverem/
├── README.md
├── pyproject.toml
├── src
│   └── elso_mcp_szerverem
│       ├── __init__.py
│       └── server.py
└── uv.lock
```

## Megjegyzés

Ellenőrizd az előfeltételeket és telepítsd azokat, ha szükséges. Ezeket megtalálod a [fő README.md fájlban](../README.md).

## 1. lépés: Alap MCP szerver

Viszonylag könnyű dolgunk lesz, mert néhány kódsor megírásáva máris lesz egy MCP szerverünk. Lássuk a lépéseket:

1. Virtuális környezet létrehozása és a függőségek telepítése:

```bash
uv sync
```

2. Az `src/elso_mcp_szerverem` mappában hozzunk létre egy **server.py** fájlt a következő tartalommal:

```python
# Szükséges Python csomagok importálása
from mcp.server.mcpserver import MCPServer

# MCP szerver példány létrehozása
mcp = MCPServer("Első MCP Szerverem")

# A fő program indítása - entry point
if __name__ == "__main__":
    print(f"{mcp.name} indul...")
    # A szerver futtatása a helyi gépen a 8000-es porton
    mcp.run(host="0.0.0.0", port=8000)
```

3. Szerver indítása:

   ```bash
   uv run python src/elso_mcp_szerverem/server.py
   ```

Ezzel készen is van az első MCP szerverünk. Habár nem képes még semmire, már fut és elérhető a megadott porton.

## 2. lépés: Képességek hozzáadása

Ebben a lépésben felruházzuk a szerverünket különböző képességekkel, azaz létrehozunk új eszközöket (tools), új erőforrásokat (resources), és promptokat (prompts).

1. Állítsuk le az előzőleg indított MCP szervert, ha még fut. Ehhez használhatjuk a terminálban a `Ctrl+C` kombinációt.

2. Nyissuk meg az `src/elso_mcp_szerverem/server.py` fájlt, és adjuk hozzá az első eszközt (tool) a következő módon:

```python
# Első eszköz (tool) létrehozása
@mcp.tool(name="Osszeadas", description="Két szám összeadására szolgáló eszköz")
def osszeadas(a: int, b: int) -> int:
    """A két számot összeadja és a végeredményt adja vissza."""
    return a + b
```

Ez az eszköz az alábbit csinálja: két számot ad össze, és visszaadja az eredményt. Amint láthatjuk, ez alapvetően egy egyszerű python függvény, amelyet az MCP szerver eszközeként regisztráltunk. Ami viszont az MCP rendszer számára használhatóvá teszi azt a dekorátor (`@mcp.tool`) és a megfelelő metainformációk (név és leírás) biztosítása.

3. Mentse el a fájlt, és indítsa újra az MCP szervert a következő parancs segítségével:

   ```bash
   uv run python src/elso_mcp_szerverem/server.py
   ```
