# Fejlett MCP Szerver

Ez az [első MCP szerver](../elso-mcp-szerverem/README.md) következő lépése. A váz ugyanaz: Python 3.13, `uv`, a forráskód a `src` mappában. Az import `from mcp.server.mcpserver import MCPServer`.

Ott egy `server.py`-ban volt egy tool, egy resource és egy prompt, és a szerver a gépen indult. Itt a szerver a Cloud Runon fut. A kliens a Service URL `/mcp` útvonalára csatlakozik. A képességek külön fájlok, a `server.py` létrehozza az `MCPServer`-t, és a külső MCP-k tooljai is ezen az egy szerveren jelennek meg.

Protokoll: [2026-07-28](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro).

## Tartalomjegyzék

- [Mappastruktúra](#mappastruktúra)
- [Mit ad a szerver](#mit-ad-a-szerver)
- [Külső MCP-k](#külső-mcp-k)
- [GitHub személyes token](#github-személyes-token)
- [Kulcsok](#kulcsok)
- [Claude Desktop helyi integráció](#claude-desktop-helyi-integráció)
   - [E2E teszt](#e2e-teszt)
- [Cloud Run](#cloud-run)
   - [Bejelentkezés](#bejelentkezés)
   - [Jogosultság](#jogosultság)
   - [Prepare](#prepare)
   - [env.gcp](#envgcp)
   - [Deploy](#deploy)
   - [CI/CD](#cicd)
- [Remote integráció](#remote-integráció)
   - [Claude Desktop](#claude-desktop)
   - [Cursor](#cursor)
   - [Claude Code](#claude-code)
   - [ChatGPT Codex](#chatgpt-codex)
- [Remote tesztelés](#remote-tesztelés)
   - [MCP Inspector](#mcp-inspector)
   - [Claude Desktopban](#claude-desktopban)
   - [Cursorban és Codexben](#cursorban-és-codexben)
   - [Próbák](#próbák)
- [Törlés](#törlés)

## Mappastruktúra

```plaintext
fejlett-mcp-szerver/
├── README.md
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── package.json
├── package-lock.json
├── .dockerignore
├── .env.example
├── externals.json
├── externals.cloudrun.json
├── scripts
│   ├── prepare-gcp-deploy.sh
│   └── teardown-gcp-deploy.sh
├── examples
│   └── cursor_mcp.json
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
| `hely_kereses`, `elorejelzes`, `levegominoseg` | [Open-Meteo MCP](https://github.com/cyanheads/open-meteo-mcp-server), HTTP: `https://open-meteo.caseyjhand.com/mcp`. Kulcs nincs. A nem kereskedelmi használat ingyenes, az adat az [Open-Meteo](https://open-meteo.com/) (CC BY 4.0). |
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

## GitHub személyes token

A GitHub MCP classic personal access tokent használ. Ezt a GitHubon hozod létre, ezekkel a jogokkal:

1. GitHubon: **Settings**, **Developer settings**, **Personal access tokens**, **Tokens (classic)**.
2. **Generate new token**, **Generate new token (classic)**.
3. **Note**: adj neki egy nevet, ami erre a szerverre utal.
4. **Expiration**: állíts lejáratot.
5. Jelöld be ezeket a scope-okat:
   - `repo` — a saját és a szervezet repói, a fájltartalom, az issue-k és a pull requestek.
   - `read:org` — szervezeti tagság. Az `issue_kereses` és a `pr_kereses` org-szintű kereséséhez kell.
6. **Generate token**. A tokent a GitHub csak egyszer mutatja. Másold ki.
7. Ha a szervezet SAML SSO-t használ: a token sorában **Configure SSO**, majd az org mellett **Authorize**.

A token ezután a [Kulcsok](#kulcsok) szerint a helyi `.env` fájlba kerül. Értékét ne írd a repóba.

## Kulcsok

Az árfolyam és az időjárás kulcs nélkül megy. A GitHubhoz másold a példát, és töltsd ki:

```bash
cp .env.example .env
```

| Változó | Mire kell |
| --- | --- |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | A fent létrehozott GitHub token. |
| `QR_OUTPUT_DIR` | A QR PNG mappája. Üresen a Letöltések. |
| `MCP_EXTERNALS` | Külső MCP-k JSON-ja, vagy `off`. |
| `MCP_TRANSPORT` | `stdio` (alap) vagy `streamable-http`. |
| `HOST`, `PORT` | HTTP kötés. Alap: `0.0.0.0`, `8080`. |

Üres kulcsnál az a külső MCP nem indul. A Cloud Runon a GitHub token a Secret Managerből jön, a neve ugyanaz: `GITHUB_PERSONAL_ACCESS_TOKEN`. Az árfolyam és az időjárás kulcs nélkül megy. Az időjárás ugyanaz a HTTP MCP helyben és a Cloud Runon.

## Claude Desktop helyi integráció

A menük ugyanazok, mint az [első MCP szervernél](../elso-mcp-szerverem/README.md): **Settings**, **Developer**, **Edit Config**. A fájl macOS-en `~/Library/Application Support/Claude/claude_desktop_config.json`.

A `"mcpServers"` kulcsba ez kerül. A `<A_TE_HELYI_ELERESI_UTVONALAD>` a `trn-ai-mcp` szülőmappája. Ments, és indítsd újra a Claude Desktopot.

```json
"mcpServers": {
  "Fejlett MCP Szerver": {
    "command": "/opt/homebrew/bin/uv",
    "args": [
      "--directory",
      "<A_TE_HELYI_ELERESI_UTVONALAD>/trn-ai-mcp/fejlett-mcp-szerver",
      "run",
      "python",
      "src/fejlett_mcp_szerver/server.py"
    ]
  }
}
```

A **Developer** listában a **Fejlett MCP Szerver** szerepel. A **Connections** sorában ott van az **Összeadás**, az **Úti cél**, az **Utazási adatok** erőforrás és az **Utazás** prompt.

### E2E teszt

1. Nyiss egy chatet.
2. **+**, **Connections**, **Add from Fejlett MCP Szerver**, **Utazás (prompt)**.
3. Ugyanígy add hozzá az **Utazási adatok** resource-t.
4. A város Cancun, az ország Mexikó, az összeg 1000000, a pénznem HUF.
5. Enter. A modell az `uticel` toolból veszi az időzónát és a pénznemet, majd az időt, az időjárást és az átváltást azokkal a toolokkal kéri.

## Cloud Run

A parancsokat a `fejlett-mcp-szerver` mappából futtasd, ebben a sorrendben. A projekt azonosító, a GitHub repo, a secret neve és a token nem része a parancsoknak: a projekt a `PROJECT_ID` környezeti változó, a repo a `git origin`, a token a `GITHUB_PERSONAL_ACCESS_TOKEN`.

### Bejelentkezés

Két külön hitelesítés van. Nem helyettesítik egymást.

A scriptek a **gcloud parancssori** fiókot használják. A `PROJECT_ID` a shellben él, utána a scriptek külön parancsként mennek:

```bash
export PROJECT_ID="<Te GCP Projekted ID-ja>"
gcloud auth login
gcloud config set project "$PROJECT_ID"
```

Az **Application Default Credentials** a klienskönyvtáraké és a Terraformé. A Prepare és a Deploy ezt nem használja:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project "$PROJECT_ID"
```

A szkript nem ad szerepet a bejelentkezett fióknak. A projekten előre legyen meg a deployhoz szükséges jogosultság (Owner, vagy a megfelelő admin szerepek).

A Prepare a [GitHub személyes token](#github-személyes-token) értékét a helyi `.env` fájlból a Secret Managerbe teszi. A Cloud Run a futásidejű fiókkal olvassa. A deploy fiók nem kap olvasási jogot a secretre. Üres tokennél a szerver elindul, a GitHub toolok kimaradnak.

### Jogosultság

Két service account van.

- A futásidejű fiók a Cloud Runon fut. Csak a registry olvasása a saját repón, és a GitHub MCP secret olvasása.
- A deploy fiók a GitHub Actionsé. Csak image írás a saját repóba, `roles/run.developer`, és a futásidejű fiók használata. Workload Identity csak a `main` ág `refs/heads/main` refjére szól, és csak arra a GitHub repóra, ami az `origin` remote.

Az első, kézi deploy a service-t nyilvánosan hívhatóvá teszi. A CI deploy ezt a kapcsolót nem adja meg újra, ezért nem kell hozzá `setIamPolicy`.

### Prepare

A felhős erőforrásokat hozza létre. Image még nem készül, a Cloud Run service sem indul. A `fejlett-mcp-szerver` mappából:

```bash
./scripts/prepare-gcp-deploy.sh
```

Létrejön az API-engedély, az Artifact Registry repo, a két service account, a Workload Identity OIDC provider, és a GitHub token secretje a helyi `.env`-ből. Ha a `gh` be van lépve, a `GCP_*` Actions változók is bekerülnek a repóra. A végén a script felülírja a `fejlett-mcp-szerver/.env.gcp` fájlt.

Az alapérték elég. Más érték a [env.gcp](#envgcp) táblázat szerint a script előtt exportálható, utána ugyanez a parancs fut újra. A fájl szerkesztése a GCP-t nem változtatja meg, mert a script ezt a fájlt nem olvassa.

### env.gcp

Helyi jegyzék arról, amit a Prepare létrehozott. Gitignore alatt van, ne commitold. A Törlés letörli. A következő Prepare felülírja.

| Kulcs | Jelentése | Módosítás a script előtt |
| --- | --- | --- |
| `PROJECT_ID` | A GCP projekt azonosítója. | `export PROJECT_ID="<Te GCP Projekted ID-ja>"` |
| `REGION` | A régió. Alap: `europe-west1`. | `export REGION="<a régió>"` |
| `ARTIFACT_REPO` | Az Artifact Registry repo neve. Alap: `fejlett-mcp-szerver`. | `export ARTIFACT_REPO="<a repo neve>"` |
| `SERVICE_NAME` | A Cloud Run service neve. Alap: `fejlett-mcp-szerver`. | `export SERVICE_NAME="<a service neve>"` |
| `RUNTIME_SA` | A futásidejű fiók emailje. A script a névből rakja össze. | `export RUNTIME_SA_NAME="<a név>"` |
| `DEPLOY_SA` | A CI deploy fiók emailje. | `export DEPLOY_SA_NAME="<a név>"` |
| `IMAGE_URI` | Az image teljes címe, a régióból, a projektből, a repóból és a tagből. | `export IMAGE_NAME="<a név>"` és `export IMAGE_TAG="<a tag>"` |
| `MCP_TRANSPORT` | A Cloud Run transportja. Mindig `streamable-http`. | A Prepare ezt így írja. |
| `MCP_EXTERNALS` | A konténer külső MCP fájlja. Mindig `/app/externals.cloudrun.json`. | A Prepare ezt így írja. |
| `GITHUB_MCP_SECRET` | A secret neve, nem a token. Alap: `<SERVICE_NAME>-github-pat`. | `export GITHUB_MCP_SECRET="<a secret neve>"` |
| `WIF_PROVIDER` | Az OIDC provider teljes erőforrásneve. | `export WIF_POOL="<a pool>"` és `export WIF_PROVIDER="<a provider>"` |

### Deploy

Ugyanaz az előkészítés, utána `linux/amd64` image, push, Cloud Run. A konténer az `externals.cloudrun.json` fájlt használja. Az image a buildkor telepíti a Node-ot és az `exchange-rate-mcp`-t, a `penzvaltas` kulcs nélkül elérhető. Az időjárás HTTP MCP, ugyanaz a cím, mint helyben: `hely_kereses`, `elorejelzes`, `levegominoseg`. A GitHub MCP HTTP-n megy.

```bash
./scripts/prepare-gcp-deploy.sh --deploy
```

A Deploy kiírja a Service URL-t. A kliens címe ez, plusz `/mcp`. A további lépésekben ez a `<A_CLOUD_RUN_CIMED>`.

### CI/CD

A szűrő mindkét résznél a `fejlett-mcp-szerver/` mappa. A CI a saját workflow fájljára és a deploy workflow fájlra is indul. A deploy a saját workflow fájljára is indul.

A [`.github/workflows/ci-fejlett-mcp-szerver.yml`](../.github/workflows/ci-fejlett-mcp-szerver.yml) a `main` ágra nyitott pull requesten fut. Először a lint (`ruff check`), utána a tesztek (`pytest`).

A [`.github/workflows/deploy-fejlett-mcp-szerver.yml`](../.github/workflows/deploy-fejlett-mcp-szerver.yml) a `main` ágra merge után fut. OIDC-vel lép be a deploy service accounthoz. A provider, a fiók és a projekt a GitHub Actions változókban van (`GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SERVICE_ACCOUNT`, `GCP_RUNTIME_SERVICE_ACCOUNT`, és a többi `GCP_*`). A workflow fájlban nincs belőlük érték. A futás `docker build`, `docker push`, majd `gcloud run deploy`. A secret kötést az első kézi deploy teszi fel, a további deploy ezt a kötést meghagyja. A GitHub **Actions** fülön a **Deploy fejlett-mcp-szerver** futás zöld, a Cloud Run új revisiont kap.

## Remote integráció

A szerver a Cloud Runon fut. A kliens a `https://<A_CLOUD_RUN_CIMED>/mcp` címre csatlakozik. A név **Fejlett MCP Szerver**.

A Claude Desktop remote csatlakozása a Connectors felület. A `claude_desktop_config.json` csak helyi `command` indítást fogad el. Egy `"url"` mezőt kihagy, és ezt írja: not valid MCP server configurations and were skipped.

### Claude Desktop

1. **Settings**, **Connectors**, **Add custom connector**.
2. Név: **Fejlett MCP Szerver**.
3. MCP server URL: `https://<A_CLOUD_RUN_CIMED>/mcp`.
4. A szerver nyilvános, OAuth nincs. A varázslóban a **No sign-in** lehetőséget válaszd. Request header nem kell.
5. **Connect**.
6. A **Connections** listában a **Fejlett MCP Szerver** szerepel, rajta az **Összeadás**, az **Úti cél** és az `utazas://adatok`.

### Cursor

A minta: [`examples/cursor_mcp.json`](examples/cursor_mcp.json). Globális fájl: `~/.cursor/mcp.json`. Egy projektre: `<projekt>/.cursor/mcp.json`.

```json
{
  "mcpServers": {
    "Fejlett MCP Szerver": {
      "url": "https://<A_CLOUD_RUN_CIMED>/mcp"
    }
  }
}
```

Mentsd a fájlt. A Cursor **Settings**, **MCP** listájában a **Fejlett MCP Szerver** connected.

### Claude Code

```bash
claude mcp add --scope user --transport http "Fejlett MCP Szerver" "https://<A_CLOUD_RUN_CIMED>/mcp"
```

Ellenőrzés: `claude mcp list`. Új session, majd `/mcp`. A **Fejlett MCP Szerver** legyen connected.

### ChatGPT Codex

A Codex a nevében nem enged szóközt.

```bash
codex mcp add Fejlett-MCP-Szerver --url "https://<A_CLOUD_RUN_CIMED>/mcp"
```

`codex mcp list`. A beállítás a `~/.codex/config.toml` fájlban van.

## Remote tesztelés

Ezek a Cloud Runon lévő szervert érik. A `penzvaltas` az image-beli árfolyam MCP. Az időjárás toolok is ezen a szerveren vannak.

### MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

1. Transport: **Streamable HTTP**.
2. URL: `https://<A_CLOUD_RUN_CIMED>/mcp`.
3. Csatlakozás. A státusz zöld.
4. **Tools**, **Összeadás** (`osszead`): `a` = `12`, `b` = `30`. Az eredmény `42`.
5. **Resources**, `utazas://adatok`. A szövegben benne van a `DTL250113` foglalás.
6. **Prompts**, **Utazás**: `varos` Cancun, `orszag` Mexikó, `osszeg` 1000000, `penznem` HUF. A kész üzenet az `uticel` toolt kéri.

### Claude Desktopban

1. Nyiss egy chatet.
2. **+**, **Connections**, **Add from Fejlett MCP Szerver**.
3. `Add össze a 12-t és a 30-at.` Az **Összeadás** `42`-t ad.
4. `Milyen időzóna és pénznem van Cancunban, Mexikóban?` Az **Úti cél** `America/Cancun` és `MXN`.
5. `Ki vagyok a GitHubon?` A **GitHub profil** tool válaszol, ha a PAT a Secret Managerben van.

### Cursorban és Codexben

Nyiss egy Agent chatet, vagy indítsd a `codex` parancsot.

`Add össze a 12-t és a 30-at.`

Ha jóváhagyást kér, **Allow**. Az **Összeadás** `42`-t ad.

### Próbák

- „Add össze a 12-t és a 30-at.”
- „Mennyi az idő az `Asia/Tokyo` zónában?”
- „Miről szól a https://example.com?”
- „Hány óra van 2026-09-25 10:00 és 2026-09-25 12:30 között?”
- „Generálj egy 20 karakteres jelszót.”
- „Milyen időzóna és pénznem van Cancunban, Mexikóban?”
- „Mennyi az árfolyam HUF-ról MXN-re?” A **Pénzváltás** válaszol.
- „Milyen az időjárás Cancunban?” Az **Előrejelzés** válaszol.
- Resource `utazas://adatok`: foglalás DTL250113.
- „Ki vagyok a GitHubon?”
- „Keress Python MCP repo-kat.”

## Törlés

A felhős erőforrások törlése. A `PROJECT_ID` a [Bejelentkezés](#bejelentkezés) óta a shellben van. A parancs a `fejlett-mcp-szerver` mappából megy.

```bash
./scripts/teardown-gcp-deploy.sh --force
```

Ha az API-k bekapcsolva maradjanak, ugyanez a script a `--keep-apis` kapcsolóval.
