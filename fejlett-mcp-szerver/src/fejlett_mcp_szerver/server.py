"""Az MCP szerver példánya és a transport belépési pontja.

Az első MCP szerverben a tool, a resource és a prompt ebben a fájlban volt.
Itt a server.py létrehozza az MCPServert, a tools, resources és prompts
mappák register() függvénye pedig felteszi a képességeket.

Ugyanaz a szerver beszél stdio-n (Claude Desktop) és Streamable HTTP-n (Cloud Run).
A transport futásidejű választás; a toolok, resource-ok és prompok változatlanok.
"""

from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer

from fejlett_mcp_szerver import __version__
from fejlett_mcp_szerver.prompts import register_prompts
from fejlett_mcp_szerver.resources import register_resources
from fejlett_mcp_szerver.tools import register_tools
from fejlett_mcp_szerver.externals import expand_process_path, external_lifespan

mcp = MCPServer(
    "fejlett-mcp-szerver",
    version=__version__,
    instructions=(
        "Vannak eszközeid. Használd őket; ezekre ne memóriából válaszolj. "
        "Ne kérdezd meg, melyik tool kell — a felhasználó szavaiból válaszd ki. "
        "Összeadás: osszead. "
        "Aktuális idő: aktualis_ido. "
        "Úti cél, időzóna, helyi pénznem: uticel. "
        "Pénzváltás, árfolyam: penzvaltas. "
        "Időjárás: először hely_kereses, utána elorejelzes a koordinátákkal. "
        "Levegőminőség: levegominoseg, szintén a hely_kereses koordinátáival. "
        "Weboldal, URL, miről szól: weboldal_osszefoglalo. "
        "QR-kód: qr_kod. "
        "Két időpont között eltelt idő: idokulonbseg. "
        "Jelszó: jelszo. "
        "GitHub felhasználó: github_profil. Repók: repo_kereses. "
        "Fájl egy repóban: fajl_tartalom. "
        "Nyitott issue-k egy repóban: issue_lista. "
        "Nyitott PR-ok egy repóban: pr_lista. "
        "Issue-k egy egész szervezetben: issue_kereses, org:NÉV is:open. "
        "PR-ok egy egész szervezetben: pr_kereses, org:NÉV is:open."
    ),
    lifespan=external_lifespan,
)

register_tools(mcp)
register_resources(mcp)
register_prompts(mcp)


def main() -> None:
    # Stdio-n a szabványos kimenet a protokoll. Ide nem írunk printet.
    expand_process_path()
    if os.getenv("MCP_TRANSPORT", "stdio") == "stdio":
        mcp.run()
        return

    mcp.run(
        transport="streamable-http",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
    )


if __name__ == "__main__":
    main()
