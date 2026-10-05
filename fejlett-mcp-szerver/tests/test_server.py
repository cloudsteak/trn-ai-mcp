import pytest
from mcp import Client

from fejlett_mcp_szerver.server import mcp


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client():
    async with Client(mcp, raise_exceptions=True) as connected:
        yield connected


@pytest.mark.anyio
async def test_osszead(client: Client) -> None:
    result = await client.call_tool("osszead", {"a": 2, "b": 3})
    assert result.structured_content == {"result": 5}


@pytest.mark.anyio
async def test_uticel(client: Client) -> None:
    result = await client.call_tool("uticel", {"varos": "Cancun", "orszag": "Mexikó"})
    text = result.structured_content["result"]
    assert "időzóna: America/Cancun" in text
    assert "pénznem: MXN" in text


@pytest.mark.anyio
async def test_aktualis_ido(client: Client) -> None:
    result = await client.call_tool("aktualis_ido", {"timezone": "Europe/Budapest"})
    text = result.structured_content["result"]
    assert "T" in text


@pytest.mark.anyio
async def test_weboldal_osszefoglalo(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    html = (
        "<html><head><title>Demo</title>"
        "<meta name='description' content='A sample site.'></head>"
        "<body><p>Hello</p></body></html>"
    )
    monkeypatch.setattr(
        "fejlett_mcp_szerver.tools.weboldal_osszefoglalo.fetch_landing", lambda url: html
    )
    result = await client.call_tool("weboldal_osszefoglalo", {"url": "example.com"})
    text = result.structured_content["result"]
    assert "https://example.com" in text
    assert "Demo" in text
    assert "A sample site." in text


@pytest.mark.anyio
async def test_idokulonbseg(client: Client) -> None:
    result = await client.call_tool(
        "idokulonbseg",
        {"start": "2026-09-25T10:00", "end": "2026-09-25T12:30"},
    )
    data = result.structured_content
    assert data["hours"] == 2.5
    assert data["minutes"] == 150


@pytest.mark.anyio
async def test_jelszo(client: Client) -> None:
    result = await client.call_tool("jelszo", {"length": 12})
    assert len(result.structured_content["result"]) == 12


@pytest.mark.anyio
async def test_qr_kod(
    client: Client, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("QR_OUTPUT_DIR", str(tmp_path))
    result = await client.call_tool("qr_kod", {"data": "https://example.com"})
    images = [block for block in result.content if block.type == "image"]
    texts = [block.text for block in result.content if block.type == "text"]
    assert images
    assert images[0].mime_type == "image/png"
    assert any("Mentve ide:" in text for text in texts)
    assert list(tmp_path.glob("qr-*.png"))


def _resource_text(result) -> str:
    return "\n".join(block.text for block in result.contents if hasattr(block, "text"))


@pytest.mark.anyio
async def test_resources(client: Client) -> None:
    listed = await client.list_resources()
    uris = {str(resource.uri) for resource in listed.resources}
    assert uris == {
        "utazas://adatok",
        "training://ability-list",
    }

    trip = _resource_text(await client.read_resource("utazas://adatok"))
    assert "Utazás: Budapest > Cancun" in trip
    assert "Indulás: holnap, 06:00 (Budapesti idő)" in trip
    assert "Érkezés: holnap 20:45 (Cancuni idő)" in trip
    assert "Cím: Blvd. Kukulcán Km 14.5, Zona Hotelera, 77500 Cancún" in trip
    assert "Foglalási azonosító: DTL250113" in trip
    assert "1000000 forint" in trip

    abilities = _resource_text(await client.read_resource("training://ability-list"))
    assert "toolok:" in abilities
    assert "- osszead" in abilities
    assert "resource-ok:" in abilities
    assert "- utazas://adatok" in abilities
    assert "- Oktató (prompt)" in abilities
    assert "- Alfa (prompt)" in abilities
    assert "- Ügyvéd (prompt)" in abilities
    assert "promptok:" in abilities
    assert "- Utazás (prompt)" in abilities
    assert "- Holnapi időjárás (prompt)" in abilities
    assert "külső toolok:" in abilities
    assert "- penzvaltas" in abilities


@pytest.mark.anyio
async def test_utazas_prompt(client: Client) -> None:
    listed = await client.list_prompts()
    names = {prompt.name for prompt in listed.prompts}
    titles = {prompt.name: prompt.title for prompt in listed.prompts}
    assert names == {"oktato", "alfa", "ugyved", "utazas", "holnapi_idojaras"}
    assert titles["oktato"] == "Oktató (prompt)"
    assert titles["alfa"] == "Alfa (prompt)"
    assert titles["ugyved"] == "Ügyvéd (prompt)"
    assert titles["utazas"] == "Utazás (prompt)"
    assert titles["holnapi_idojaras"] == "Holnapi időjárás (prompt)"

    result = await client.get_prompt(
        "utazas",
        {
            "varos": "Cancun",
            "orszag": "Mexikó",
            "osszeg": "1000000",
            "penznem": "HUF",
        },
    )
    message = result.messages[0]
    assert message.role == "user"
    text = message.content.text
    assert "Ide utazom: Cancun, Mexikó. Viszek 1000000 HUF összeget." in text
    assert "uticel" in text
    assert "penzvaltas" in text
    assert "qr_kod" not in text
    assert "weboldal" not in text


@pytest.mark.anyio
async def test_hangnem_prompts(client: Client) -> None:
    expected = {
        "oktato": "A CloudMentor nevében válaszolj, nyugodtan, kedvesen és szerényen.",
        "alfa": "alfa generációs szlengben beszélsz.",
        "ugyved": "ügyvédként válaszolsz.",
    }
    for name, snippet in expected.items():
        result = await client.get_prompt(name)
        message = result.messages[0]
        assert message.role == "user"
        text = message.content.text
        assert snippet in text
        if name == "oktato":
            assert "Csak Cloud és AI kérdésre válaszolj." in text
            assert "csak Cloud vagy AI kérdés lehet." in text
            continue
        assert "A téma bármi lehet." in text


@pytest.mark.anyio
async def test_holnapi_idojaras_prompt(client: Client) -> None:
    result = await client.get_prompt("holnapi_idojaras", {"hely": "Budapest"})
    message = result.messages[0]
    assert message.role == "user"
    assert message.content.text == (
        "Mondd meg a holnapi időjárást. Az elorejelzes toolt hívd, "
        "ne emlékezetből válaszolj.\n\n"
        "Hely: Budapest"
    )


@pytest.mark.anyio
async def test_lists_expected_tools(client: Client) -> None:
    listed = await client.list_tools()
    names = {tool.name for tool in listed.tools}
    assert names == {
        "osszead",
        "aktualis_ido",
        "weboldal_osszefoglalo",
        "qr_kod",
        "idokulonbseg",
        "jelszo",
        "uticel",
    }
