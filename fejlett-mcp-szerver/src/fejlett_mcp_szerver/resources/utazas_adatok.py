"""Az utazás adatai. Indulás és érkezés holnap, dátum nélkül."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer


def register(mcp: MCPServer) -> None:
    @mcp.resource("utazas://adatok", title="Utazási adatok (resource)")
    def utazas_adatok() -> str:
        """Járat, szállás, foglalás és összeg. Az indulás és az érkezés holnap van."""
        return (
            "Utazás: Budapest > Cancun\n"
            "Indulás: holnap, 06:00 (Budapesti idő)\n"
            "Érkezés: holnap 20:45 (Cancuni idő)\n"
            "Szállás: Travel CLub Resort\n"
            "Cím: Blvd. Kukulcán Km 14.5, Zona Hotelera, 77500 Cancún\n"
            "Check-in: 21:00\n"
            "Foglalási azonosító: DTL250113\n"
            "Összeg: 1000000 forint.\n"
        )
