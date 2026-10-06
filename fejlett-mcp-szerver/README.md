# Fejlett MCP Szerver

Ez az [első MCP szerver](../elso-mcp-szerverem/README.md) következő lépése. A váz ugyanaz: Python 3.13, `uv`, a forráskód a `src` mappában. Az import `from mcp.server.mcpserver import MCPServer`.

Ott egy `server.py`-ban volt egy tool, egy resource és egy prompt, és a szerver a gépen indult. Itt a szerver a Cloud Runon fut. A kliens a Service URL `/mcp` útvonalára csatlakozik. A képességek külön fájlok, a `server.py` létrehozza az `MCPServer`-t, és a külső MCP-k tooljai is ezen az egy szerveren jelennek meg.

Protokoll: [2026-07-28](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro).

## Tartalomjegyzék

- [Mappastruktúra](#mappastruktúra)
- [Mit ad a szerver](#mit-ad-a-szerver)
- [Külső MCP-k](#külső-mcp-k)
- [Kulcsok](#kulcsok)
- [Claude Desktop helyi integráció](#claude-desktop-helyi-integráció)
   - [E2E teszt](#e2e-teszt)
- [Cloud Run](#cloud-run)
   - [Bejelentkezés](#bejelentkezés)
   - [GitHub PAT](#github-pat)
   - [Jogosultság](#jogosultság)
   - [Törlés](#törlés)
   - [Prepare](#prepare)
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
├── externals.cloudrun.json
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

Üres kulcsnál az a külső MCP nem indul. A Cloud Runon a token a Secret Managerből jön, a neve ugyanaz: `GITHUB_PERSONAL_ACCESS_TOKEN`. Az `npx`-es árfolyam és időjárás a konténerben nincs.

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

A parancsokat a repo gyökeréből futtasd, ebben a sorrendben. A projekt azonosító, a GitHub repo, a secret neve és a token nem része a parancsoknak: a projekt a `PROJECT_ID` környezeti változó, a repo a `git origin`, a token a `GITHUB_PERSONAL_ACCESS_TOKEN`.

### Bejelentkezés

Két külön hitelesítés van. Nem helyettesítik egymást.

A scriptek a **gcloud parancssori** fiókot használják. A `PROJECT_ID` a shellben él, utána a scriptek külön parancsként mennek:

```bash
export PROJECT_ID="$PROJECT_ID"
gcloud auth login
gcloud config set project "$PROJECT_ID"
```

Az **Application Default Credentials** a klienskönyvtáraké és a Terraformé. A Prepare és a Deploy ezt nem használja:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project "$PROJECT_ID"
```

A szkript nem ad szerepet a bejelentkezett fióknak. A projekten előre legyen meg a deployhoz szükséges jogosultság (Owner, vagy a megfelelő admin szerepek).

### GitHub PAT

A GitHub Actions a GCP-be OIDC-vel lép be. A GitHub MCP ettől függetlenül bearer tokent vár. A tokent a shellben add meg. A `read -rs` nem írja ki:

```bash
read -rs GITHUB_PERSONAL_ACCESS_TOKEN
export GITHUB_PERSONAL_ACCESS_TOKEN
```

Ha a változó üres, a Prepare a helyi `.env` fájlból olvassa (az gitignore alatt van). Feltölti a Secret Managerbe. A Cloud Run a futásidejű service accounttal olvassa, a konténerben a változó neve `GITHUB_PERSONAL_ACCESS_TOKEN`. A deploy fiók nem kap olvasási jogot a secretre. Üres tokennél a szerver elindul, a GitHub toolok kimaradnak.

### Jogosultság

Két service account van.

- A futásidejű fiók a Cloud Runon fut. Csak a registry olvasása a saját repón, és a GitHub MCP secret olvasása.
- A deploy fiók a GitHub Actionsé. Csak image írás a saját repóba, `roles/run.developer`, és a futásidejű fiók használata. Workload Identity csak a `main` ág `refs/heads/main` refjére szól, és csak arra a GitHub repóra, ami az `origin` remote.

Az első, kézi deploy a service-t nyilvánosan hívhatóvá teszi. A CI deploy ezt a kapcsolót nem adja meg újra, ezért nem kell hozzá `setIamPolicy`.

### Törlés

Cloud Run service, Artifact Registry repo, mindkét service account, a secret és a Workload Identity pool. A `--force` megerősítés nélkül töröl, és kikapcsolja az API-kat is. A `serviceusage` API-t a szkript nem kapcsolja ki.

```bash
./scripts/teardown-gcp-deploy.sh --force
```

Ha az API-k maradjanak a következő Prepare előtt, add hozzá a `--keep-apis` kapcsolót.

### Prepare

API-k, Artifact Registry, a két service account, OIDC provider, a secret, és ha a `gh` be van lépve, a GitHub Actions változók. Image még nem készül. A `fejlett-mcp-szerver/.env.gcp` helyi fájl, gitignore alatt van, ne commitold.

```bash
./scripts/prepare-gcp-deploy.sh
```

### Deploy

Ugyanaz az előkészítés, utána `linux/amd64` image, push, Cloud Run. A konténer az `externals.cloudrun.json` fájlt használja: csak a GitHub HTTP MCP. Node és `npx` nincs az image-ben.

```bash
./scripts/prepare-gcp-deploy.sh --deploy
```

A Deploy kiírja a Service URL-t. A kliens címe ez, plusz `/mcp`. A további lépésekben ez a `<A_CLOUD_RUN_CIMED>`.

### CI/CD

A [`.github/workflows/deploy-fejlett-mcp-szerver.yml`](../.github/workflows/deploy-fejlett-mcp-szerver.yml) a `main` ágra merge után fut, ha a `fejlett-mcp-szerver/` vagy maga a workflow változott. OIDC-vel lép be a deploy service accounthoz. A provider, a fiók és a projekt a GitHub Actions változókban van (`GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SERVICE_ACCOUNT`, `GCP_RUNTIME_SERVICE_ACCOUNT`, és a többi `GCP_*`). A workflow fájlban nincs belőlük érték.

A futás `docker build`, `docker push`, majd `gcloud run deploy`. A secret kötést nem írja felül: azt az első kézi deploy teszi fel. PR-t a `main`-re merge-ölj. A GitHub **Actions** fülön a **Deploy fejlett-mcp-szerver** futás zöld, a Cloud Run új revisiont kap.

## Remote integráció

A szerver a Cloud Runon fut. A kliens a `https://<A_CLOUD_RUN_CIMED>/mcp` címre csatlakozik. A név **Fejlett MCP Szerver**.

A Claude Desktop remote csatlakozása a Connectors felület. A `claude_desktop_config.json` az első szerver helyi folyamatáé.

### Claude Desktop

1. **Settings**, **Connectors**, **Add custom connector**.
2. Név: **Fejlett MCP Szerver**.
3. MCP server URL: `https://<A_CLOUD_RUN_CIMED>/mcp`.
4. A szerver nyilvános, OAuth nincs. A varázslóban a hitelesítés nélküli lehetőséget válaszd.
5. Mentsd. A **Connections** listában a **Fejlett MCP Szerver** szerepel, rajta az **Összeadás**, az **Úti cél** és az `utazas://adatok`.

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

Ezek a Cloud Runon lévő szervert érik. Az árfolyam és az időjárás `npx` MCP, azok a konténerben nincsenek.

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
- Resource `utazas://adatok`: foglalás DTL250113.
- „Ki vagyok a GitHubon?”
- „Keress Python MCP repo-kat.”
