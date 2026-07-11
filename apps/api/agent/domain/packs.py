"""Domain skill packs — Screening, OSINT, KYB, Rules."""

from __future__ import annotations

from typing import Any

from agent.bedrock import is_configured, safe_invoke
from agent.connectors.registry import kyb_connector, osint_connector, sanctions_connector
from agent.domain.sanctions import ofac_available, screen_ofac
from agent.tools.case_tools import read_alert
from agent.tools.rag_tools import suggest_policy
from db.repository import get_alert

OFAC_SOURCE = "OFAC SDN (public list)"


def _apply_ofac_to_alert(alert: dict[str, Any], ofac: dict[str, Any]) -> dict[str, Any]:
    """Persist real OFAC result onto the alert dict (in-memory; caller may save)."""
    hit = bool(ofac.get("hit"))
    score = float(ofac.get("score") or 0.0)
    pep = bool((alert.get("signals") or {}).get("pep_hit"))
    status = "hit" if hit else ("review" if pep else "clear")
    matched = ofac.get("matched_name")
    program = ofac.get("program")
    note_parts = []
    if hit and matched:
        note_parts.append(f"OFAC SDN match: {matched}" + (f" [{program}]" if program else ""))
        note_parts.append(f"score={score:.0%}")
    elif ofac.get("list_available"):
        note_parts.append(f"No OFAC SDN hit (best score {score:.0%})")
    else:
        note_parts.append("OFAC list unavailable — screening skipped")
    screening = {
        "status": status,
        "matches": 1 if hit else 0,
        "note": "; ".join(note_parts),
        "match_confidence": score,
        "matched_name": matched,
        "program": program,
        "list_sources": [OFAC_SOURCE] if ofac.get("list_available") else ["OFAC SDN (unavailable)"],
        "ofac": {
            "hit": hit,
            "score": score,
            "matched_name": matched,
            "program": program,
            "uid": ofac.get("uid"),
            "entry_count": ofac.get("entry_count"),
        },
    }
    alert["sanctions_screening"] = screening
    signals = dict(alert.get("signals") or {})
    signals["sanctions_hit"] = hit
    alert["signals"] = signals
    if hit and "sanctions_proximity" not in (alert.get("risk_tags") or []):
        alert.setdefault("risk_tags", []).append("sanctions_proximity")
    return screening


def screening_with_policy_overlay(
    alert_id: str,
    message: str,
    high_risk_countries: list[str] | None = None,
    alert: dict[str, Any] | None = None,
) -> dict[str, Any]:
    alert = alert or get_alert(alert_id)
    if not alert:
        return {"error": "Alert not found"}

    ofac: dict[str, Any] | None = None
    if ofac_available():
        ofac = screen_ofac(alert.get("customer_name"), alert.get("counterparty"))
        s = _apply_ofac_to_alert(alert, ofac)
        source = OFAC_SOURCE
        confidence = float(ofac.get("score") or 0.0)
    else:
        conn = sanctions_connector()
        screening = conn.screen(name=alert["customer_name"], alert=alert)
        s = screening.data
        source = f"simulated:{screening.source}" if not str(screening.source).startswith("simulated") else screening.source
        confidence = float(screening.confidence)

    countries = high_risk_countries or []
    if countries:
        note = f"Session policy overlay: treat {', '.join(countries)} as elevated risk."
    else:
        note = s.get("note", "Standard screening lists applied.")

    fields = [
        {"label": "Status", "value": str(s.get("status", "unknown")).upper()},
        {"label": "Matches", "value": str(s.get("matches", 0))},
        {"label": "PEP", "value": "Yes" if s.get("pep") or (alert.get("signals") or {}).get("pep_hit") else "No"},
        {"label": "Source", "value": source},
        {"label": "Score", "value": f"{int(confidence * 100)}%"},
    ]
    if ofac is not None:
        fields.append({"label": "Matched Name", "value": str(ofac.get("matched_name") or "—")})
        fields.append({"label": "Program", "value": str(ofac.get("program") or "—")})

    cards = [
        {
            "type": "screening",
            "title": "Sanctions Screening",
            "fields": fields,
        },
        {
            "type": "metrics",
            "title": "Review Metrics",
            "fields": [
                {"label": "Approved", "value": "—"},
                {"label": "PEP FP Cleared", "value": "2" if s.get("status") == "review" else "0"},
                {"label": "Sanctions FP", "value": str(s.get("matches", 0))},
            ],
        },
    ]
    match_bit = ""
    if ofac and ofac.get("hit"):
        match_bit = f" matched_name=**{ofac.get('matched_name')}**, program=**{ofac.get('program')}**."
    reply = (
        f"Screening for **{alert['customer_name']}** / counterparty **{alert.get('counterparty', '—')}** "
        f"({alert_id}): status **{s.get('status')}**, {s.get('matches', 0)} match(es), "
        f"score {confidence:.0%}.{match_bit} {note} (source: {source})"
    )
    if message and is_configured():
        reply = safe_invoke(
            f"{message}\n\nContext: {reply}",
            system=(
                "You are a Sanctions Screening Agent for a crypto VASP. Be concise. "
                "Interpret OFAC SDN match results; never invent a hit that is not in the context. "
                "Never clear a confirmed OFAC hit."
            ),
            fallback=reply,
        )
    return {
        "reply": reply,
        "cards": cards,
        "type": "screening",
        "ofac": ofac,
        "source": source,
        "sanctions_screening": s,
    }

def osint_research(entity_name: str, alert_id: str | None = None) -> dict[str, Any]:
    alert = read_alert(alert_id) if alert_id else None
    name = entity_name or (alert or {}).get("customer_name", "Unknown entity")
    conn = osint_connector()
    osint = conn.lookup(name=name, alert=alert)
    d = osint.data
    cards = [
        {
            "type": "business",
            "title": "Business Information",
            "fields": [
                {"label": "Legal Name", "value": d.get("legal_name", name)},
                {"label": "Entity Type", "value": d.get("entity_type", "—")},
                {"label": "Status", "value": str(d.get("status", "—")).title()},
                {"label": "Jurisdiction", "value": d.get("jurisdiction", (alert or {}).get("country", "US"))},
                {"label": "Source", "value": osint.source},
            ],
        },
        {
            "type": "classification",
            "title": "Industry Classification",
            "fields": [
                {"label": "Sector", "value": d.get("sector", "—")},
                {"label": "Risk Tier", "value": (alert or {}).get("risk_level", "medium").upper()},
                {"label": "Adverse Media", "value": d.get("adverse_media", "—")},
                {"label": "Confidence", "value": f"{int(osint.confidence * 100)}%"},
            ],
        },
    ]
    reply = (
        f"OSINT summary for **{name}**: {d.get('status','active')} entity, "
        f"{d.get('sector','VASP')} sector, {d.get('adverse_media','no adverse media')}."
        f" (source: {osint.source} [simulated], confidence: {int(osint.confidence * 100)}%)"
    )
    if is_configured():
        ctx = f"Entity: {name}, country: {(alert or {}).get('country', 'N/A')}"
        reply = safe_invoke(
            f"Summarize OSINT business research for:\n{ctx}",
            system="You are an OSINT Search Agent. Output 2-3 sentences, professional tone.",
            fallback=reply,
        )
    return {"reply": reply, "cards": cards, "type": "osint"}


def kyb_due_diligence(alert_id: str) -> dict[str, Any]:
    alert = get_alert(alert_id)
    if not alert:
        return {"error": "Alert not found"}
    partner = alert.get("partner", "Unknown VASP")
    conn = kyb_connector()
    kyb = conn.verify(partner=partner, alert=alert)
    d = kyb.data
    cards = [
        {
            "type": "kyb",
            "title": "Entity Verification",
            "fields": [
                {"label": "Partner", "value": d.get("partner", partner)},
                {"label": "Partner ID", "value": d.get("partner_id", alert.get("partner_id", "—"))},
                {"label": "License Status", "value": str(d.get("license_status", "—")).title()},
                {"label": "UBO Risk", "value": str(d.get("ubo_risk", "—")).title()},
                {"label": "Source", "value": kyb.source},
            ],
        },
        {
            "type": "red_flags",
            "title": "Red Flag Detection",
            "fields": [
                {"label": "Mixer Exposure", "value": "Yes" if alert.get("signals", {}).get("mixer_exposure") else "No"},
                {"label": "Travel Rule", "value": alert.get("travel_rule_status", "—")},
                {"label": "KYT Score", "value": str(alert.get("kyt_score", "—"))},
            ],
        },
    ]
    return {
        "reply": f"KYB review for **{partner}** — {d.get('license_status','registered')} (source: {kyb.source} [simulated], confidence: {int(kyb.confidence*100)}%).",
        "cards": cards,
        "type": "kyb",
    }


def rule_assistant_suggest(message: str) -> dict[str, Any]:
    suggestion = suggest_policy()
    cards = [
        {
            "type": "rule",
            "title": "Suggested Rule",
            "fields": [
                {"label": "Rule", "value": suggestion.get("suggestion", "Review mixer + Travel Rule combo")},
                {"label": "Rationale", "value": suggestion.get("suggestion", "Review mixer + Travel Rule combo")[:120]},
                {"label": "Fire Rate (mock)", "value": "0.31%"},
            ],
        },
    ]
    reply = suggestion.get("suggestion", "Consider lowering KYT threshold for new wallets under $5k.")
    if is_configured():
        reply = safe_invoke(
            message or "Suggest an AML monitoring rule for crypto on-ramps.",
            system="You are a Rule Assistant Agent. Suggest one concrete monitoring rule in plain English.",
            fallback=reply,
        )
    return {"reply": reply, "cards": cards, "type": "rule"}
