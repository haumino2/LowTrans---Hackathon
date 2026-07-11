from __future__ import annotations

from agent.connectors.base import ConnectorResult


class MockSanctionsConnector:
    def screen(self, *, name: str, alert: dict) -> ConnectorResult:
        s = alert.get("sanctions_screening", {}) or {}
        status = (s.get("status") or "unknown").lower()
        matches = int(s.get("matches", 0) or 0)
        pep = bool((alert.get("signals") or {}).get("pep_hit"))
        conf = float(s.get("match_confidence") or (0.92 if status == "hit" else 0.55 if status == "review" else 0.18))
        sources = s.get("list_sources") or ["OFAC SDN (fallback)", "PEP World-Check (simulated)"]
        evidence = []
        if status == "hit":
            evidence.append(
                {
                    "list": "OFAC SDN (fallback)",
                    "matched_name": name,
                    "score": conf,
                    "program": s.get("program") or "SDGT",
                    "citation": "simulated://sanctions-fallback",
                }
            )
        elif pep:
            evidence.append(
                {
                    "list": "PEP",
                    "matched_name": name,
                    "score": 0.71,
                    "program": "Domestic PEP",
                    "citation": "simulated:pep-worldcheck",
                }
            )
        return ConnectorResult(
            data={
                "status": status,
                "matches": matches,
                "pep": pep,
                "note": s.get("note") or "OFAC list unavailable — simulated fallback screening.",
                "list_sources": sources,
                "match_confidence": conf,
                "matched_name": s.get("matched_name"),
                "program": s.get("program"),
                "evidence": evidence,
            },
            source="simulated:sanctions",
            confidence=conf,
        )


class MockOsintConnector:
    def lookup(self, *, name: str, alert: dict | None) -> ConnectorResult:
        tags = (alert or {}).get("risk_tags") or []
        adverse = (
            "Mixer-adjacent cluster mentions in darkweb intel (simulated)"
            if "mixer_exposure" in tags
            else "None flagged (simulated)"
        )
        return ConnectorResult(
            data={
                "legal_name": name,
                "entity_type": "Natural person / LLC (simulated registry)",
                "status": "active",
                "jurisdiction": (alert or {}).get("country", "US"),
                "sector": "Virtual Asset Service Provider customer",
                "adverse_media": adverse,
                "sources": [
                    {"title": "OpenCorporates snapshot (simulated)", "url": "simulated://opencorporates", "date": "2025-06-01"},
                    {"title": "Adverse media sweep (simulated)", "url": "simulated://osint-feed", "date": "2025-07-01"},
                ],
                "confidence_note": "Simulated OSINT pack — not a live vendor lookup",
            },
            source="simulated:osint",
            confidence=0.62 if "mixer_exposure" in tags else 0.5,
        )


class MockKybConnector:
    def verify(self, *, partner: str, alert: dict) -> ConnectorResult:
        return ConnectorResult(
            data={
                "partner": partner,
                "partner_id": alert.get("partner_id", "—"),
                "license_status": "registered (simulated)",
                "license_jurisdiction": alert.get("country", "US"),
                "ubo_risk": "elevated" if (alert.get("signals") or {}).get("pep_hit") else "low",
                "travel_rule_ready": alert.get("travel_rule_status") == "complete",
                "last_review": "2025-05-12",
                "registry_citations": ["simulated:vasp-registry", "simulated:msb-license"],
            },
            source="simulated:kyb",
            confidence=0.68,
        )