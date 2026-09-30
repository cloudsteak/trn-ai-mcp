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

### Első eszköz hozzáadása

1. Állítsuk le az előzőleg indított MCP szervert, ha még fut. Ehhez használhatjuk a terminálban a `Ctrl+C` kombinációt.

2. Nyissuk meg az `src/elso_mcp_szerverem/server.py` fájlt, és adjuk hozzá az első eszközt (tool) a következő módon:

```python
# Első eszköz (tool) létrehozása
@mcp.tool(name="Osszeadas", title="Összeadás", description="Két szám összeadására szolgáló eszköz")
def osszeadas(a: int, b: int) -> int:
    """A két számot összeadja és a végeredményt adja vissza."""
    return a + b
```

Ez az eszköz az alábbit csinálja: két számot ad össze, és visszaadja az eredményt. Amint láthatjuk, ez alapvetően egy egyszerű python függvény, amelyet az MCP szerver eszközeként regisztráltunk. Ami viszont az MCP rendszer számára használhatóvá teszi azt a dekorátor (`@mcp.tool`) és a megfelelő metainformációk (név és leírás) biztosítása.

3. Mentse el a fájlt, és indítsa újra az MCP szervert a következő (új) parancs segítségével:

   ```bash
   uv run mcp run src/elso_mcp_szerverem/server.py
   ```

_Megjegyzés: A `python server.py` csak lefuttatja a fájlt, ezért a fájl végén kell egy indítósor (mcp.run()), különben a program hibaüzenet nélkül kilép. Az `mcp run server.py` magától megtalálja és elindítja a szervert, így nem kell hozzá indítósor._

Nincs hiba, tehát működik az első eszközünk. Adjunk hozzá most egy erőforrást is.

### Első erőforrás hozzáadása

Erőforrásunk egy naplóbejegyzést olvas be a webshop logfájljából. Így ez olvasható lesz bármelyik ágens számára, amely hozzáfér az MCP szerverhez.

1. Állítsuk le az előzőleg indított MCP szervert, ha még fut. Ehhez használhatjuk a terminálban a `Ctrl+C` kombinációt.

2. Nyissuk meg az `src/elso_mcp_szerverem/server.py` fájlt, és adjuk hozzá az első erőforrást (resource) a következő módon:

```python
# Első erőforrás (resource) létrehozása: logfájl beolvasása
@mcp.resource(uri="log://webshop_log", name="WebshopLogfajlBeolvasasa", title="Webshop logfájl beolvasása (erőforrás)", description="A webshop logfájljának beolvasására szolgáló erőforrás")
def logfajl_beolvasasa() -> str:
    """Beolvassa a megadott logfájlt és visszaadja a tartalmát."""
    fajlnev = "log/webshop-api.log"
    with open(fajlnev, "r", encoding="utf-8") as f:
        return f.read()
```

3. Mentse el a fájlt, és indítsa újra az MCP szervert a következő parancs segítségével:

   ```bash
   uv run mcp run src/elso_mcp_szerverem/server.py
   ```

_Megjegyzés: A `python server.py` csak lefuttatja a fájlt, ezért a fájl végén kell egy indítósor (mcp.run()), különben a program hibaüzenet nélkül kilép. Az `mcp run server.py` magától megtalálja és elindítja a szervert, így nem kell hozzá indítósor._

Ha nincs hiba, az első erőforrásunk is működik, és elérhető az MCP szerveren keresztül.

### Első prompt hozzáadása

Egyszerű prompt megoldást implementálunk. Azt mondjuk az AI-alkalmazásnak, hogy több lépést is hajtson végre egymás után. Így nem kell begépelnünk ezt többször.

1. Állítsuk le az előzőleg indított MCP szervert, ha még fut. Ehhez használhatjuk a terminálban a `Ctrl+C` kombinációt.

2. Nyissuk meg az `src/elso_mcp_szerverem/server.py` fájlt, és adjuk hozzá az első promptot (prompt) a következő módon:

```python
# Első prompt (prompt) létrehozása: több lépés végrehajtása egymás után
@mcp.prompt(name="IncidensJelentes", title="Incidens jelentés (prompt)", description="Incidens jelentés készítése naplóbejegyzés alapján")
def incidens_jelentes() -> str:
    """Végrehajtja a megadott promptban szereplő lépéseket egymás után. Naplóbejegízések elemzése, hibasorok és figyelmeztetési sorok összegzése, majd kiküldése egy megadott email címre."""
    return (
        "Te egy AI-alkalmazás vagy, amely képes több lépést végrehajtani egymás után.\n"
        "Elemezd a webshop logfájljának bejegyzéseit, azonosítsd a hibasorokat és figyelmeztetéseket, ha van ilyen.\n"
        "Majd készíts egy összefoglalót az esemény lefolyásáról, időbélyegekkel, a valószínű kiváltó okokkal együtt.\n"
        "Tegyél javaslatot, hogy mit kellene felülvizsgálni, vagy részletesebben elemezni a rendszeren.\n"
        "Add össze eszközzel a hiba és a figyelmeztetést tartalmazó sorok számát.\n"
        "Ha van FATAL hiba, akkor az előző összeadás eredményéhez add azt is hozzá, amihez szintén eszközt használj.\n"
        "Készíts egy grafikus timeline-t is, majd a szöveges összefoglalóval és az összeadás eredményével együtt küldd el nekem az email címemre.\n"
        "Ügyelj arra, hogy olyan legyen a grafika, hogy email-ben is látványos és jól olvasható legyen.\n"
        "Az email tárgya: [INCIDENS ÖSSZEFOGLALÓ] - Webshop leállás incidens dátuma\n"
        "Ha nem adtam meg email címet, akkor kérd be tőlem."
    )
```

3. Mentse el a fájlt, és indítsa újra az MCP szervert a következő parancs segítségével:

   ```bash
   uv run mcp run src/elso_mcp_szerverem/server.py
   ```

   Ha nincs hiba, az első promptunk is működik, és elérhető az MCP szerveren keresztül.

4. Állítsa le az MCP szervert a `Ctrl+C` kombinációval a terminálban.

Következő lépésben az MCP Inspector-t, ami egy vizuákis tesztelő- és hibakereső alkalmazás, ismerjük meg. Majd integráljuk az MCP szerverünket Claude Desktop alkalmazással.
