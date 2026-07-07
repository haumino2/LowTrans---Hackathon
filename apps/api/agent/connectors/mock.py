from __future__ import annotations

from agent.connectors.base import ConnectorResult


class MockSanctionsConnector:
    def screen(self, *, name: str, alert: dict) -> ConnectorResult:
        s = alert.get("sanctions_screening", {}) or {}
        return ConnectorResult(
            data={
                "status": (s.get("status") or "unknown").lower(),
                "matches": int(s.get("matches", 0) or 0),
                "pep": bool((alert.get("signals") or {}).get("pep_hit")),
                "note": s.get("note") or "Standard screening lists applied (mock).",
            },
            source="mock:sanctions",
            confidence=0.55,
        )


class MockOsintConnector:
    def lookup(self, *, name: str, alert: dict | None) -> ConnectorResult:
        return ConnectorResult(
            data={
                "legal_name": name,
                "entity_type": "LLC (mock registry)",
                "status": "active",
                "jurisdiction": (alert or {}).get("country", "US"),
                "sector": "Virtual Asset Service Provider",
                "adverse_media": "None flagged (mock)",
            },
            source="mock:osint",
            confidence=0.5,
        )


class MockKybConnector:
    def verify(self, *, partner: str, alert: dict) -> ConnectorResult:
        return ConnectorResult(
            data={
                "partner": partner,
                "partner_id": alert.get("partner_id", "—"),
                "license_status": "registered (mock)",
                "ubo_risk": "low",
            },
            source="mock:kyb",
            confidence=0.55,
        )

