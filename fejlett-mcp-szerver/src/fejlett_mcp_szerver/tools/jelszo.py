"""Adott hosszúságú véletlen jelszó készítése."""

from __future__ import annotations

import logging
import secrets
import string

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)

_SYMBOLS = "!@#$%&*-_=+"
_POOL = string.ascii_letters + string.digits + _SYMBOLS
_MIN_LENGTH = 8
_MAX_LENGTH = 128


def new_password(length: int) -> str:
    if length < _MIN_LENGTH or length > _MAX_LENGTH:
        raise ValueError(f"A hossz {_MIN_LENGTH} és {_MAX_LENGTH} között legyen.")
    chars = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(_SYMBOLS),
    ]
    chars.extend(secrets.choice(_POOL) for _ in range(length - 4))
    for index in range(len(chars) - 1, 0, -1):
        swap = secrets.randbelow(index + 1)
        chars[index], chars[swap] = chars[swap], chars[index]
    return "".join(chars)


def register(mcp: MCPServer) -> None:
    @mcp.tool(title="Jelszógeneráló")
    def jelszo(length: int = 16) -> str:
        """Biztonságos, véletlen jelszót készít betűkből, számokból és szimbólumokból.

        Akkor hívd, ha a felhasználó jelszót kér.

        Args:
            length: Jelszó hossza, 8–128. Alapértelmezett: 16.
        """
        logger.info("jelszo length=%s", length)
        return new_password(length)
