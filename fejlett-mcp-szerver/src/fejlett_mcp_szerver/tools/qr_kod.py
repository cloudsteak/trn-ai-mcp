"""QR-kód PNG készítése, és mentése egy megnyitható helyre."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path

import qrcode
from mcp.server.mcpserver import Image, MCPServer
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

_QR_SIZE = 800


def render_qr_png(data: str) -> bytes:
    image = qrcode.make(data, border=2)
    image = image.resize((_QR_SIZE, _QR_SIZE), resample=PILImage.Resampling.NEAREST)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def output_dir() -> Path:
    raw = os.getenv("QR_OUTPUT_DIR")
    folder = Path(raw).expanduser() if raw else Path.home() / "Downloads"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_qr_png(png: bytes) -> Path:
    path = output_dir() / f"qr-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
    path.write_bytes(png)
    return path


def register(mcp: MCPServer) -> None:
    @mcp.tool(title="QR-kód")
    def qr_kod(data: str) -> list:
        """QR-kódot készít, megjeleníti, és PNG-ként elmenti a Letöltések mappába.

        Akkor hívd, ha a felhasználó QR-kódot kér.

        Args:
            data: A kódolandó tartalom, például egy webcím.
        """
        logger.info("qr_kod bytes=%s", len(data))
        if not data.strip():
            raise ValueError("Adj meg szöveget vagy URL-t a kódoláshoz.")
        png = render_qr_png(data)
        path = save_qr_png(png)
        logger.info("qr_kod saved %s", path)
        return [Image(data=png, format="png"), f"Mentve ide: {path}"]
