"""Behavioral pattern engine — structuring / smurfing / velocity heuristics."""

from __future__ import annotations

from typing import Any


def analyze_behavior(alert: dict[str, Any]) -> dict[str, Any]:
    amount = float(alert.get("amount_usd") or 0)
    tags = set(alert.get("risk_tags") or [])
    signals = alert.get("signals") or {}
    direction = str(alert.get("direction") or "").lower()
    connections = int(alert.get("connections") or 0)
    account_age = int(alert.get("account_age_days") or signals.get("wallet_age_days") or 0)

    patterns: list[dict[str, Any]] = []

    # Classic CTR evasion band
    if 9000 <= amount <= 9999 or "structuring" in tags or signals.get("structuring"):
        patterns.append(
            {
                "id": "structuring_band",
                "name": "Structuring / smurfing band",
                "severity": "high",
                "detail": f"Amount ${amount:,.0f} sits in classic $9k–$10k evasion window",
                "confidence": 0.78,
            }
        )

    # Rapid new-account high value
    if account_age <= 3 and amount >= 10000:
        patterns.append(
            {
                "id": "velocity_new_account",
                "name": "New-account velocity",
                "severity": "medium",
                "detail": f"Account age {account_age}d with ${amount:,.0f} {direction}",
                "confidence": 0.7,
            }
        )

    # Fan-out / dense counterparty graph
    if connections >= 12 and direction == "withdrawal":
        patterns.append(
            {
                "id": "fanout_withdrawal",
                "name": "High fan-out withdrawal",
                "severity": "medium",
                "detail": f"{connections} connections on withdrawal path",
                "confidence": 0.65,
            }
        )

    # Round-number layering hint
    if amount >= 20000 and amount % 10000 == 0:
        patterns.append(
            {
                "id": "round_layering",
                "name": "Round-number layering hint",
                "severity": "low",
                "detail": f"Exact round amount ${amount:,.0f}",
                "confidence": 0.55,
            }
        )

    severity_rank = {"high": 3, "medium": 2, "low": 1}
    top = max(patterns, key=lambda p: severity_rank.get(p["severity"], 0)) if patterns else None

    if patterns and top:
        summary = (
            f"Behavioral engine: {len(patterns)} pattern(s) — {top['name']} "
            f"({top.get('severity', 'low')})"
        )
    else:
        summary = "No behavioral pattern matched"

    return {
        "patterns": patterns,
        "hit": bool(patterns),
        "top_pattern": top,
        "summary": summary,
        "source": "behavioral-v2",
    }
