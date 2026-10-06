import pytest

from fejlett_mcp_szerver.tools.idokulonbseg import difference, parse_moment
from fejlett_mcp_szerver.tools.jelszo import new_password
from fejlett_mcp_szerver.tools.qr_kod import render_qr_png, save_qr_png
from fejlett_mcp_szerver.tools.uticel import lookup
from fejlett_mcp_szerver.tools.weboldal_osszefoglalo import normalize_url, summarize_html


def test_summarize_html_uses_meta_description() -> None:
    html = """
    <html><head>
      <title>CloudMentor</title>
      <meta name="description" content="Training for cloud engineers.">
    </head><body>
      <script>ignore()</script>
      <p>Welcome to the landing page of the course.</p>
    </body></html>
    """
    text = summarize_html(html, "https://example.com")
    assert "url: https://example.com" in text
    assert "cím: CloudMentor" in text
    assert "összefoglaló: Training for cloud engineers." in text
    assert "ignore()" not in text
    assert "Welcome to the landing page" in text


def test_normalize_url_adds_https() -> None:
    assert normalize_url("example.com") == "https://example.com"


def test_date_difference_hours_and_minutes() -> None:
    result = difference("2026-09-25T10:00", "2026-09-25 12:30")
    assert result["hours"] == 2.5
    assert result["minutes"] == 150
    assert result["duration"] == "2 óra 30 perc"


def test_parse_european_date() -> None:
    moment = parse_moment("25.09.2026 14:05")
    assert moment.year == 2026
    assert moment.month == 9
    assert moment.day == 25
    assert moment.hour == 14


def test_password_length_and_classes() -> None:
    password = new_password(20)
    assert len(password) == 20
    assert any(char.islower() for char in password)
    assert any(char.isupper() for char in password)
    assert any(char.isdigit() for char in password)


def test_uticel_cancun() -> None:
    text = lookup("Cancun", "Mexikó")
    assert "időzóna: America/Cancun" in text
    assert "pénznem: MXN" in text


def test_uticel_ignores_accents() -> None:
    text = lookup("tokio", "japan")
    assert "időzóna: Asia/Tokyo" in text
    assert "pénznem: JPY" in text


def test_uticel_unknown_city() -> None:
    text = lookup("Reykjavik", "Izland")
    assert text.startswith("Nincs adat erről a városról:")


def test_qr_png_header() -> None:
    from io import BytesIO

    from PIL import Image

    png = render_qr_png("https://example.com")
    assert png.startswith(b"\x89PNG")
    assert Image.open(BytesIO(png)).size == (800, 800)


def test_save_qr_png(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QR_OUTPUT_DIR", str(tmp_path))
    path = save_qr_png(render_qr_png("https://example.com"))
    assert path.parent == tmp_path
    assert path.suffix == ".png"
    assert path.read_bytes().startswith(b"\x89PNG")
