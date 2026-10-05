"""Két időpont különbsége órában és percben."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)

_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%d.%m.%Y",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
)


def parse_moment(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        moment = None
        for fmt in _FORMATS:
            try:
                moment = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        if moment is None:
            raise ValueError(
                f"Nem értelmezhető: {value!r}. ISO formátum, pl. 2026-09-25T14:30"
            ) from None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def difference(start: str, end: str) -> dict[str, float | int | str]:
    first = parse_moment(start)
    second = parse_moment(end)
    total_minutes = int(round(abs((second - first).total_seconds()) / 60))
    hours_part, minutes_part = divmod(total_minutes, 60)
    return {
        "hours": round(total_minutes / 60, 2),
        "minutes": total_minutes,
        "duration": f"{hours_part} óra {minutes_part} perc",
    }


def register(mcp: MCPServer) -> None:
    @mcp.tool(title="Időkülönbség")
    def idokulonbseg(start: str, end: str) -> dict[str, float | int | str]:
        """Két dátum vagy időpont különbsége órában és percben. A sorrend mindegy.

        Akkor hívd, ha eltelt időt, időkülönbséget kérdeznek.

        Args:
            start: Első időpont, például 2026-09-25T10:00.
            end: Második időpont, például 2026-09-25 12:30.
        """
        logger.info("idokulonbseg start=%s end=%s", start, end)
        return difference(start, end)
