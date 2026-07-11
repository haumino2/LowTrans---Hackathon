"""Deterministic AML policy gates — never overridden by LLM Arbiter."""

from __future__ import annotations

from typing import Any


def evaluate_hard_gates(alert: dict[str, Any]) -> list[dict[str, Any]]:
    """Return policy hits that force ESCALATE (or hard REVIEW)."""
    hits: list[dict[str, Any]] = []
    signals = alert.get("signals") or {}
    sanctions = alert.get("sanctions_screening") or {}
    travel = str(alert.get("travel_rule_status", "")).lower()
    amount = float(alert.get("amount_usd") or 0)
    tags = alert.get("risk_tags") or []

    has_sanctions = bool(signals.get("sanctions_hit")) or str(sanctions.get("status", "")).lower() == "hit"
    if has_sanctions:
        hits.append(
            {
                "code": "OFAC_HIT",
                "severity": "critical",
                "decision": "ESCALATE",
                "disposition": "escalate_edd",
                "message": "Sanctions / OFAC match detected — hard escalate per policy",
                "confidence": 0.95,
            }
        )

    if travel == "missing" and amount > 3000:
        hits.append(
            {
                "code": "TRAVEL_RULE_MISSING",
                "severity": "high",
                "decision": "ESCALATE",
                "disposition": "escalate_edd",
                "message": f"Travel Rule missing for ${amount:,.0f} — IVMS101 required",
                "confidence": 0.88,
            }
        )

    mixer = bool(signals.get("mixer_exposure")) or "mixer_exposure" in tags
    if mixer and travel in ("missing", "incomplete") and amount > 3000:
        hits.append(
            {
                "code": "MIXER_TRAVEL_RULE",
                "severity": "critical",
                "decision": "ESCALATE",
                "disposition": "block_transaction",
                "message": "Mixer exposure with incomplete Travel Rule on high-value transfer",
                "confidence": 0.94,
            }
        )

    return hits


def apply_gates_to_decision(
    hits: list[dict[str, Any]],
    *,
    soft_decision: str,
    soft_confidence: float,
    soft_disposition: str,
) -> tuple[str, float, str, bool]:
    """Merge soft (ML/LLM) proposal with hard gates. Gates always win."""
    escalate = [h for h in hits if h.get("decision") == "ESCALATE"]
    if escalate:
        top = max(escalate, key=lambda h: float(h.get("confidence", 0)))
        return (
            "ESCALATE",
            float(top.get("confidence", 0.9)),
            str(top.get("disposition", "escalate_edd")),
            True,
        )
    return soft_decision, soft_confidence, soft_disposition, False
