# fejlett-mcp-szerver

Ez az [első MCP szerver](../elso-mcp-szerverem/README.md) következő lépése. A váz ugyanaz: Python 3.13, `uv`, a forráskód a `src` mappában. Az import `from mcp.server.mcpserver import MCPServer`.

Ott egy `server.py`-ban volt egy tool, egy resource és egy prompt, és a szerver a 8000-es porton indult. Itt a képességek külön fájlok, a `server.py` létrehozza az `MCPServer`-t (név, verzió, instructions, lifespan), és a három `register()` függvény fűzi fel őket. A lifespan a külső MCP-ket a háttérben csatolja. A kliens továbbra is csak ehhez az egy szerverhez csatlakozik. A saját toolok, resource-ok és promptok itt jelennek meg, és ide kerülnek az `externals.json` külső MCP-jeinek tooljai is. A `rename` saját nevet ad nekik.

Protokoll: [2026-07-28](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro). Verzió: `0.1.0`.

## Mappastruktúra

```plaintext
fejlett-mcp-szerver/
├── README.md
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── .dockerignore
├── .env.example
├── externals.json
├── examples
│   └── claude_desktop_config.json
├── src
│   └── fejlett_mcp_szerver
│       ├── __init__.py
│       ├── __main__.py
│       ├── server.py
│       ├── externals.py
│       ├── tools
│       ├── resources
│       └── prompts
└── tests
```

Új saját tool: egy fájl a `tools` mappában, import, és egy sor a `_TOOLS` listában. Új resource és prompt ugyanígy a saját mappájában. Új külső MCP: egy elem az `externals.json`-ban.

## Mit ad a szerver

| Név | Honnan |
| --- | --- |
| `osszead` | saját tool, két szám összege (`a`, `b`, tizedes is) |
| `aktualis_ido` | saját tool, IANA időzóna (alap: `Europe/Budapest`), ISO dátum |
| `weboldal_osszefoglalo` | saját tool, nyitóoldal címe, leírása és rövid szövege; `https://` nélkül is |
| `qr_kod` | saját tool, 800×800 PNG a válaszban, és fájl a Letöltésekben |
| `idokulonbseg` | saját tool, két időpont különbsége órában és percben; a sorrend mindegy |
| `jelszo` | saját tool, véletlen jelszó, hossz 8–128 (alap: 16) |
| `uticel` | saját tool, rögzített városlista: időzóna és pénznem |
| `utazas_adatok` | resource, `utazas://adatok` |
| `ability_list` | resource, `training://ability-list` |
| Oktató (prompt) | hangnem, csak Cloud és AI kérdés |
| Alfa (prompt) | hangnem, bármilyen téma |
| Ügyvéd (prompt) | hangnem, bármilyen téma |
| Utazás (prompt) | `varos`, `orszag`, `osszeg` (alap: 1000000), `penznem` (alap: HUF) |
| Holnapi időjárás (prompt) | `hely` (alap: Budapest), az `elorejelzes` toolt hívja |
| `penzvaltas` | [exchange-rate-mcp](https://www.npmjs.com/package/exchange-rate-mcp), stdio |
| `elorejelzes`, `riasztasok`, `levegominoseg` | [@smarterweather/mcp-weather](https://www.npmjs.com/package/@smarterweather/mcp-weather), stdio |
| `github_profil`, `repo_kereses`, `fajl_tartalom`, `issue_lista`, `pr_lista`, `issue_kereses`, `pr_kereses` | [GitHub MCP](https://github.com/github/github-mcp-server), HTTP: `https://api.githubcopilot.com/mcp/` |

Az `uticel` ezeket a városokat ismeri: Cancun, Budapest, Bécs, Prága, London, Párizs, Róma, Barcelona, New York, Tokió, Dubai. Az ékezet és a kis-nagybetű mindegy. Ismeretlen városnál megmondja, hogy nincs adat. Alap: Cancun, Mexikó.

A `qr_kod` a PNG-t a Letöltések mappába menti (`~/Downloads`). A `QR_OUTPUT_DIR` másik mappát ad meg.

Az Utazás prompt először az `uticel` toolt hívatja, majd az időzónával és a pénznemmel az `aktualis_ido`, az `elorejelzes` és a `penzvaltas` toolt.

## Külső MCP-k

Új külső MCP: egy elem az `externals.json`-ban.

- Stdio: `command` és `args` (például `npx`). Az `env` a gyerek folyamat környezete.
- HTTP: `url`. A `headers` értéke lehet `${ENV_VALTOZO}`.
- `rename`: a külső tool neve ezen a szerveren.
- `only`: csak ezek a toolok jönnek át.
- `require_env`: ha a kulcs üres, az a külső MCP kimarad.

A `MCP_EXTERNALS` másik JSON-fájlt ad meg. Az `off` és a `none` kikapcsolja a külső MCP-ket. A tesztek ezt használják.

## Kulcsok

Az árfolyam és az időjárás kulcs nélkül megy. A GitHubhoz másold a példát, és töltsd ki:

```bash
cp .env.example .env
```

| Változó | Mire kell |
| --- | --- |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub HTTP MCP. Classic PAT: `repo` és `read:org`. SSO-nál az orgon Authorize. |
| `QR_OUTPUT_DIR` | A QR PNG mappája. Üresen a Letöltések. |
| `MCP_EXTERNALS` | Külső MCP-k JSON-ja, vagy `off`. |
| `MCP_TRANSPORT` | `stdio` (alap) vagy `streamable-http`. |
| `HOST`, `PORT` | HTTP kötés. Alap: `0.0.0.0`, `8080`. |

Üres kulcsnál az a külső MCP nem indul. A szerver azonnal válaszol. A külső MCP-k a háttérben csatlakoznak, és ha 12 másodpercen belül nem válaszolnak, kimaradnak. Az `npx`-es külső MCP-khez Node.js kell. Claude Desktop szűk `PATH`-ján a szerver a Homebrew és az nvm `bin` mappáit is felteszi.

## Telepítés

Python 3.13 és [uv](https://docs.astral.sh/uv/). Az előfeltételek a [fő README](../README.md) fájlban vannak.

```bash
cd fejlett-mcp-szerver
uv sync --group dev
```

## Indítás

A `fejlett-mcp-szerver` mappából. Argumentum nélkül a `main()` stdio-n fut, ide nem írunk `print`-et:

```bash
uv run python src/fejlett_mcp_szerver/server.py
```

Ugyanez a `main()`: `uv run fejlett-mcp-szerver` és `uv run python -m fejlett_mcp_szerver`.

HTTP-hez:

```bash
MCP_TRANSPORT=streamable-http uv run python src/fejlett_mcp_szerver/server.py
```

A Dockerfile ugyanezt a modult indítja, `MCP_TRANSPORT=streamable-http`, port 8080. Az image Python, a külső `npx` MCP-k a helyi gépen futnak az `externals.json` alapján.

## Claude Desktop

1. **Settings, Developer, Edit Config.** macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Másold be az [`examples/claude_desktop_config.json`](examples/claude_desktop_config.json) tartalmát. A kulcs neve: `Mentor Klub MCP Server`.
3. A `command` az `uv` abszolút útja (`/opt/homebrew/bin/uv`). A `--directory` a `fejlett-mcp-szerver` mappa abszolút útja.
4. Zárd be a Claude Desktopot, és indítsd újra.

## Claude Code

A szerver ugyanaz a stdio folyamat. User scope: minden projektben elérhető.

```bash
claude mcp add --scope user fejlett-mcp-szerver -- \
  /opt/homebrew/bin/uv \
  --directory /Users/tibor.kiss/dev/github.com/cloudmentor/trn-ai-mcp/fejlett-mcp-szerver \
  run python src/fejlett_mcp_szerver/server.py
```

Cseréld az `uv` és a `--directory` útvonalát, ha nálad máshol van.

| `--scope` | Hol él |
| --- | --- |
| `user` | minden projekt |
| `local` | csak az a projekt, ahonnan a parancsot futtatod (ez az alap) |
| `project` | `.mcp.json` a repó gyökerében |

Ellenőrzés: `claude mcp list`. Nyiss új Claude Code sessiont, majd `/mcp`. A `fejlett-mcp-szerver` legyen connected.

## Próbák

- „Add össze a 12-t és a 30-at.”
- „Mennyi az idő az `Asia/Tokyo` zónában?”
- „Válts át 100 eurót forintra.”
- „Miről szól a https://example.com?”
- „Generálj QR kódot erre: https://example.com” (a PNG a Letöltésekbe is kerül)
- „Hány óra van 2026-09-25 10:00 és 2026-09-25 12:30 között?”
- „Generálj egy 20 karakteres jelszót.”
- „Milyen időzóna és pénznem van Cancunban, Mexikóban?”
- Resource `utazas://adatok`: holnap 06:00 Budapest, érkezés 20:45 Cancun, foglalás DTL250113.
- Resource `training://ability-list`: toolok, resource-ok, promptok és külső toolok.
- Prompt menü: Oktató, Alfa, Ügyvéd, Utazás (Cancun, Mexikó, 1000000 HUF), Holnapi időjárás (`hely`: Budapest).
- „Milyen idő lesz holnap Budapesten?”
- „Van riasztás Miamiban?”
- „Milyen a levegő Boise-ban?”
- „Ki vagyok a GitHubon?”
- „Keress Python MCP repo-kat.”
- „Mik a nyitott issue-k a github/github-mcp-server-ben?”

## Tesztek

```bash
uv run pytest
```

A `tests/conftest.py` a `MCP_EXTERNALS=off` értéket állítja, így a tesztek nem indítanak `npx`-et.
