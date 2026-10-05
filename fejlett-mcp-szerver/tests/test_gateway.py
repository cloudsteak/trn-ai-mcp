import time

import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer

from fejlett_mcp_szerver.externals import ExternalSpec, external_lifespan, mount_client_tools


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_mounts_and_forwards_external_tool() -> None:
    other = MCPServer("fx")

    @other.tool()
    def convert(amount: float, from_currency: str, to_currency: str) -> str:
        """Convert an amount between two currencies."""
        return f"{amount} {from_currency} -> {to_currency}"

    host = MCPServer("host")

    @host.tool()
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    async with Client(other, raise_exceptions=True) as other_client:
        mounted = await mount_client_tools(
            host, other_client, "fx", {"convert": "penzvaltas"}
        )
        assert mounted == ["penzvaltas"]

        async with Client(host, raise_exceptions=True) as host_client:
            listed = await host_client.list_tools()
            names = {tool.name for tool in listed.tools}
            assert names == {"add", "penzvaltas"}
            titles = {tool.name: tool.title for tool in listed.tools}
            assert titles["penzvaltas"] == "Pénzváltás"

            result = await host_client.call_tool(
                "penzvaltas",
                {"amount": 100, "from_currency": "EUR", "to_currency": "HUF"},
            )
            text = result.content[0].text
            assert "100" in text
            assert "EUR" in text


@pytest.mark.anyio
async def test_mount_only_selected_tools() -> None:
    other = MCPServer("wx")

    @other.tool()
    def get_forecast(location: str) -> str:
        """Forecast."""
        return location

    @other.tool()
    def get_alerts(location: str) -> str:
        """Alerts."""
        return location

    host = MCPServer("host")
    async with Client(other, raise_exceptions=True) as other_client:
        mounted = await mount_client_tools(
            host, other_client, "wx", only=["get_forecast"]
        )
        assert mounted == ["get_forecast"]


@pytest.mark.anyio
async def test_hung_external_does_not_block_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("fejlett_mcp_szerver.externals._EXTERNAL_TIMEOUT_S", 30)
    monkeypatch.setattr(
        "fejlett_mcp_szerver.externals.load_externals",
        lambda: [ExternalSpec(name="slow", command="sleep", args=("30",))],
    )
    started = time.perf_counter()
    async with external_lifespan(MCPServer("host")) as clients:
        assert time.perf_counter() - started < 1
        assert clients == {}
    assert time.perf_counter() - started < 8
