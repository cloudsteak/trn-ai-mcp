"""A Cloud Run ugyanazokat a külső MCP-ket indítja, mint a helyi szerver."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_WEATHER_URL = "https://open-meteo.caseyjhand.com/mcp"


def _by_name(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["name"]: item for item in data}


def test_weather_is_the_same_free_http_mcp_locally_and_on_cloud_run() -> None:
    local = _by_name(ROOT / "externals.json")
    cloud = _by_name(ROOT / "externals.cloudrun.json")

    assert set(cloud) == {"exchange-rate", "open-meteo", "github"}
    assert local["open-meteo"] == cloud["open-meteo"]

    weather = cloud["open-meteo"]
    assert weather["url"] == _WEATHER_URL
    assert "command" not in weather
    assert "require_env" not in weather
    assert weather["rename"]["openmeteo_search_locations"] == "hely_kereses"
    assert weather["rename"]["openmeteo_get_forecast"] == "elorejelzes"
    assert weather["rename"]["openmeteo_get_air_quality"] == "levegominoseg"

    exchange = cloud["exchange-rate"]
    assert exchange["command"] == "exchange-rate-mcp"
    assert exchange["rename"]["get_exchange_rate"] == "penzvaltas"

    github = cloud["github"]
    assert github["url"] == "https://api.githubcopilot.com/mcp/"
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" in github["require_env"]
