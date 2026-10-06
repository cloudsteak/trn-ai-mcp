# GCP Logging MCP és Claude Desktop

A [fejlett MCP szerver](../fejlett-mcp-szerver/README.md) a mi Cloud Run szolgáltatásunk. Itt egy Google által futtatott MCP-t választunk ki, és azt kötjük a Claude Desktopra.

A szerver a Cloud Logging. A konzolon a Gemini Enterprise Agent Platform MCP listájában jelenik meg, a neve `logging.googleapis.com`. A Runtime oszlopban **Google MCP**, a Location **global**, a Tools **6**. A végpont: `https://logging.googleapis.com/mcp`.

A `claude_desktop_config.json` ide nem jó. Az csak helyi `command` indítást fogad el. A remote szerver a **Connectors** felület, OAuth-tal.

## Tartalomjegyzék

- [Mit látsz a konzolon](#mit-látsz-a-konzolon)
- [Toolok](#toolok)
- [Jogosultság](#jogosultság)
- [OAuth kliens](#oauth-kliens)
- [Claude Desktop](#claude-desktop)
- [Próba](#próba)

## Mit látsz a konzolon

1. Google Cloud konzol, a projekt a `<PROJECT_ID>`.
2. **Gemini Enterprise Agent Platform**, **MCP servers**.
3. A szűrő: **Name** `logging`.
4. A **Hide system-created MCP servers** legyen kikapcsolva. A Logging Google MCP, system-created.
5. A sor: `logging.googleapis.com`, leírás **MCP for Logging API**, **Google MCP**, **global**, **6** tool.

A részletek oldalon az **Overview** a szerver azonosítóját mutatja (`locations/global`), a **Tools** fül a hat tool sémáját.

A kliensnek nem ez az azonosító kell, hanem a globális HTTP végpont:

`https://logging.googleapis.com/mcp`

A szerver akkor kerül a listára, ha a Cloud Logging API be van kapcsolva a projektben. Ha a sor hiányzik:

```bash
gcloud services enable logging.googleapis.com --project=<PROJECT_ID>
```

A tool lista hitelesítés nélkül is lekérhető:

```bash
curl --location 'https://logging.googleapis.com/mcp' \
  --header 'content-type: application/json' \
  --header 'accept: application/json, text/event-stream' \
  --data '{ "method": "tools/list", "jsonrpc": "2.0", "id": 1 }'
```

A válaszban hat tool van. A hívásuk már OAuth-ot kér. A szerver által hirdetett scope: `https://www.googleapis.com/auth/logging.admin`.

## Toolok

| Tool | Mire való | Kötelező mező |
| --- | --- | --- |
| `list_log_names` | Melyik logokban van bejegyzés | `parent`: `projects/<PROJECT_ID>` |
| `list_buckets` | Log bucketek | `parent`: `projects/<PROJECT_ID>` |
| `list_views` | Egy bucket nézetei | `parent`: `projects/<PROJECT_ID>/locations/global/buckets/_Default` |
| `list_log_entries` | Logbejegyzések keresése | `resourceNames`: egy elem, `projects/<PROJECT_ID>` |
| `get_bucket` | Egy bucket | `name` |
| `get_view` | Egy nézet | `name` |

A `list_log_entries` egyszerre egy resource projektet fogad. Több `resourceNames` elemre a hívás elhasal. Friss loghoz az `orderBy` értéke `timestamp desc`. A `filter` a [Logging query language](https://docs.cloud.google.com/logging/docs/view/logging-query-language).

## Jogosultság

A bejelentkezett Google fiókon, a `<PROJECT_ID>` projekten:

- MCP Tool User (`roles/mcp.toolUser`) — tool hívás, `mcp.tools.call`
- Logging Admin (`roles/logging.admin`) — a Logging toolok

A projekt Owner mindkettőt tartalmazza. Ha a fiók nem Owner, a két role-t külön kell megadni.

## OAuth kliens

A Claude a csatlakozót a saját felhőjéből hívja, a böngészős Google bejelentkezés a `claude.ai` címre tér vissza. A kliens típusa ezért **Web application**, akkor is, ha a Claude Desktop a gépen fut.

1. Google Cloud konzol, **Google Auth Platform**, **Branding**. Az app neve a Google consent képernyőn jelenik meg. Ajánlott név: `Mentor Klub Cloud MCP`.
2. **Audience**: **External**.
3. **Support email**: a saját címed.
4. **Clients**, **Create client**. Az **OAuth Overview** jön be. A Metrics sora: You haven't configured any OAuth clients for this project yet.
5. **Create OAuth client**.
6. Application type: **Web application**.
7. A **Name** mezőbe ajánlott név: `Mentor Klub Cloud MCP`. Ez a kliens neve a konzolon, a consent szövege az appnév marad.
8. **Authorized redirect URIs**: `https://claude.ai/api/mcp/auth_callback`.
9. Jelöld be: **Use this client for an AI-powered agent**. Ezt a klienst MCP toolokhoz jelöli ki.
10. **Create**. Másold ki a **Client ID**-t és a **Client secret**et. A secretet a Google csak egyszer mutatja. Ne kerüljön a repóba.
11. **Audience**, **Test users**, **Add users**. A saját GCP-s Gmail, amivel a konzolba be vagy jelentkezve. Nem az a fiók, amivel a Claude-ba lépsz be. **Save**.

## Claude Desktop

1. **Settings**, **Connectors**, **Add custom connector**.
2. Név: **Cloud Logging**.
3. Remote MCP server URL: `https://logging.googleapis.com/mcp`. **Continue**.
4. A varázsló OAuth-ot ismer fel. **Continue**.
5. Authentication: **Sign in now**.
6. OAuth client: **Use your own OAuth client**. Illeszd be a Client ID-t és a Client secretet.
7. A **Request headers** maradjon üres. 
8. **Add**. A Google ablakban ugyanazt a GCP-s Gmailt válaszd, amelyiket a **Test users** listába tettél.
9. A **Connections** listában a **Cloud Logging** connected. Új chatben **+**, **Connections**, kapcsold be.

## Próba

A fejlett szerver Cloud Run logjai a <PROJECT_ID> projektben vannak, ha oda deployoltad.

1. Sorold fel a log bucketeket a projects/<PROJECT_ID> alatt. A list_buckets válaszában ott a _Default.
2. Milyen lognevek vannak a projects/<PROJECT_ID> projektben? A list_log_names csak olyan logot ad, amelyikben van bejegyzés.
3. Mutasd a projects/<PROJECT_ID> utolsó ERROR súlyosságú logjait, időben visszafelé, legfeljebb 10 sort. A list_log_entries a resourceNames mezőben egy elemet kap: projects/<PROJECT_ID>. A filter tartalmazza a severity>=ERROR feltételt, az orderBy a timestamp desc, a pageSize 10.

Ha a tool 403-at ad, a fiókon hiányzik az MCP Tool User vagy a Logging Admin. A kapcsolót ilyenkor a Connectors listában távolítsd el, és add hozzá újra.
