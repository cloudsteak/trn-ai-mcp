# Multi-agent rendszerek és MCP képzés segédletek

Ez a Mentor Klub számára készült segédleteket tartalmazza a multi-agent rendszerek és az MCP képzéséhez.

## Tartalomjegyzék

- [Első MCP szerverem](#első-mcp-szerverem)
- [Előfeltételek](#előfeltételek)
- [Alap parancsok a teljesen új projekthez](#alap-parancsok-a-teljesen-új-projekthez)

## Első MCP szerverem

Az első MCP szerverem bemutatása és a projekt alapvető beállításai. Részleteket a [README](elso-mcp-szerverem/README.md) fájlban találhatsz.

## Előfeltételek

A következő előfeltételek szükségesek a projekthez:

- Python 3.13
- UV telepítése (ha még nincs telepítve):
  - Mac és Linux esetén (nem pip-ből)

  ```bash
  curl -sSL https://install.uv.io | sh
  ```

  - Windows esetén (nem pip-ből)

  ```powershell
  Invoke-WebRequest -Uri https://install.uv.io -OutFile install.ps1
  .\install.ps1
  ```

- Internetkapcsolat a csomagok letöltéséhez

## Alap parancsok a teljesen új projekthez

Ez a projekt már egy előkészített MCP szervert mutat be, így neked nem kell a kezdeti beállításokkal foglalkoznod. Ennek ellenére ideteszem azokat az alap parancsokat, amelyeket én futtattam a projekt előkészítéséhez. Én Mac-en csináltam a projektet, de hasonlóan működik Linux-on és Windows-on is.

1. UV telepítése (ha még nincs telepítve):

   ### Mac és Linux esetén (nem pip-ből)

   ```bash
   curl -sSL https://install.uv.io | sh
   ```

### Windows esetén (nem pip-ből)

```powershell
Invoke-WebRequest -Uri https://install.uv.io -OutFile install.ps1
.\install.ps1
```

2. Projekt inicializálása és mappa létrehozása a projekt számára:
   ```bash
   uv init <projekt_neve>
   cd <projekt_neve>
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
