# Szükséges Python csomagok importálása
from mcp.server.mcpserver import MCPServer

# MCP szerver példány létrehozása
mcp = MCPServer("Első MCP Szerverem")


# Első eszköz (tool) létrehozása: Összeadás
@mcp.tool(name="Osszeadas", title="Összeadás", description="Két szám összeadására szolgáló eszköz")
def osszeadas(a: int, b: int) -> int:
    """A két számot összeadja és a végeredményt adja vissza."""
    return a + b


# Első erőforrás (resource) létrehozása: logfájl beolvasása
@mcp.resource(
    uri="log://webshop_log",
    name="WebshopLogfajlBeolvasasa",
    title="Webshop logfájl beolvasása (erőforrás)",
    description="A webshop logfájljának beolvasására szolgáló erőforrás",
)
def logfajl_beolvasasa() -> str:
    """Beolvassa a megadott logfájlt és visszaadja a tartalmát."""
    fajlnev = "log/webshop-api.log"
    with open(fajlnev, "r", encoding="utf-8") as f:
        return f.read()


# Első prompt (prompt) létrehozása: több lépés végrehajtása egymás után
@mcp.prompt(
    name="IncidensJelentes", title="Incidens jelentés (prompt)",
    description="Incidens jelentés készítése naplóbejegyzés alapján",
)
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


# A fő program indítása - entry point
if __name__ == "__main__":
    print(f"{mcp.name} indul...")
    # A szerver futtatása a helyi gépen a 8000-es porton
    mcp.run(host="0.0.0.0", port=8000)
