# Első MCP szerverem

Ez egy alap MCP szerver. A hivatalos leírás: [MCP 2026-07-28](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro). A Python SDK első lépései: [first steps](https://py.sdk.modelcontextprotocol.io/get-started/first-steps/).

MCP verzió: `2026-07-28`.

## Mappastruktúra

````plaintext
elso-mcp-szerverem/
├── pyproject.toml
├── README.md
├── src
│   └── elso_mcp_szerverem
│       └── __init__.py
└── uv.lock



## Alap parancsok a teljesen új projekthez (itt nem releváns)

Ez a projekt már egy előkészített MCP szervert mutat be, így neked nem kell a kezdeti beállításokkal foglalkoznod. Ennek ellenére ideteszem azokat az alap parancsokat, amelyeket én futtattam a projekt előkészítéséhez. Én Mac-en csináltam a projektet, de hasonlóan működik Linux-on és Windows-on is.

1. UV telepítése (ha még nincs telepítve):

   ### Mac és Linux esetén (nem pip-ből)

   ```bash
   curl -sSL https://install.uv.io | sh
````

### Windows esetén (nem pip-ből)

```powershell
Invoke-WebRequest -Uri https://install.uv.io -OutFile install.ps1
.\install.ps1
```

2. Projekt inicializálása és mappa létrehozása a projekt számára:
   ```bash
   uv init elso-mcp-szerverem
   cd elso-mcp-szerverem
   ```
3. Virtuális környezet létrehozása és aktiválása:

   ### Mac és Linux esetén

   ```bash
   uv venv .venv
   source .venv/bin/activate
   ```

   _Megjegyzés: Deaktiválás a `deactivate` parancs futtatásával lehetséges._

   ### Windows esetén

   ```powershell
   uv venv .venv
   .\.venv\Scripts\activate
   ```

_Megjegyzés: Deaktiválás a `deactivate` parancs futtatásával lehetséges._

4. MCP csomag hozzáadása a projekthez

   ```bash
   uv add "mcp[cli]"
   ```

Ezzel készen is állunk a projekt fejlesztésére.

