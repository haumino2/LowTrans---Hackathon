"""Transaction risk scoring — sklearn GB preferred, explainable weighted fallback."""

from __future__ import annotations

from typing import Any

from agent.ml_model import predict_sklearn

# Weights for heuristic fallback (sum conceptually toward 0–100)
FEATURE_WEIGHTS: dict[str, float] = {
    "amount_risk": 18.0,
    "mixer_exposure": 22.0,
    "sanctions_proximity": 25.0,
    "pep_proximity": 10.0,
    "travel_rule_gap": 15.0,
    "velocity_structuring": 12.0,
    "graph_density": 10.0,
    "new_wallet": 6.0,
    "device_ip_anomaly": 8.0,
    "high_risk_jurisdiction": 8.0,
}


def _clamp(n: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, n))


def extract_features(alert: dict[str, Any]) -> dict[str, float]:
    """Map alert fields → weighted feature contributions (heuristic path)."""
    signals = alert.get("signals") or {}
    sanctions = alert.get("sanctions_screening") or {}
    tags = set(alert.get("risk_tags") or [])
    amount = float(alert.get("amount_usd") or 0)
    travel = str(alert.get("travel_rule_status", "")).lower()
    connections = int(alert.get("connections") or 0)
    wallet_age = int(signals.get("wallet_age_days") or alert.get("account_age_days") or 0)

    amount_risk = 0.0
    if amount > 50000:
        amount_risk = FEATURE_WEIGHTS["amount_risk"]
    elif amount > 25000:
        amount_risk = FEATURE_WEIGHTS["amount_risk"] * 0.7
    elif amount > 10000:
        amount_risk = FEATURE_WEIGHTS["amount_risk"] * 0.4
    elif amount > 3000:
        amount_risk = FEATURE_WEIGHTS["amount_risk"] * 0.2

    mixer = 1.0 if (signals.get("mixer_exposure") or "mixer_exposure" in tags) else 0.0
    sanctions_hit = 1.0 if (
        signals.get("sanctions_hit") or str(sanctions.get("status", "")).lower() == "hit"
    ) else (0.45 if str(sanctions.get("status", "")).lower() == "review" else 0.0)
    pep = 1.0 if signals.get("pep_hit") else 0.0

    travel_gap = 0.0
    if travel == "missing":
        travel_gap = 1.0
    elif travel in ("incomplete", "mismatch"):
        travel_gap = 0.6

    structuring = 1.0 if ("structuring" in tags or signals.get("structuring")) else 0.0
    if not structuring and amount > 0 and 9000 <= amount <= 9999:
        structuring = 0.7

    graph = 0.0
    if connections > 15:
        graph = 1.0
    elif connections > 8:
        graph = 0.6
    elif connections > 4:
        graph = 0.3

    new_wallet = 1.0 if (wallet_age < 7 or "new_wallet" in tags) else (0.4 if wallet_age < 30 else 0.0)

    device_risk = str(signals.get("device_risk", "low")).lower()
    device = 1.0 if device_risk == "high" else (0.5 if device_risk == "medium" else 0.0)
    if signals.get("ip_country") and signals.get("ip_country") != alert.get("country"):
        device = max(device, 0.7)

    hri = 1.0 if "high_risk_jurisdiction" in tags else 0.0

    return {
        "amount_risk": round(amount_risk, 2),
        "mixer_exposure": round(FEATURE_WEIGHTS["mixer_exposure"] * mixer, 2),
        "sanctions_proximity": round(FEATURE_WEIGHTS["sanctions_proximity"] * sanctions_hit, 2),
        "pep_proximity": round(FEATURE_WEIGHTS["pep_proximity"] * pep, 2),
        "travel_rule_gap": round(FEATURE_WEIGHTS["travel_rule_gap"] * travel_gap, 2),
        "velocity_structuring": round(FEATURE_WEIGHTS["velocity_structuring"] * structuring, 2),
        "graph_density": round(FEATURE_WEIGHTS["graph_density"] * graph, 2),
        "new_wallet": round(FEATURE_WEIGHTS["new_wallet"] * new_wallet, 2),
        "device_ip_anomaly": round(FEATURE_WEIGHTS["device_ip_anomaly"] * device, 2),
        "high_risk_jurisdiction": round(FEATURE_WEIGHTS["high_risk_jurisdiction"] * hri, 2),
    }


def _heuristic_score(alert: dict[str, Any]) -> dict[str, Any]:
    features = extract_features(alert)
    raw = sum(features.values())
    score = int(round(_clamp(raw * 0.95)))

    existing = alert.get("kyt_score")
    source = str(alert.get("source") or "")
    if (
        existing is not None
        and int(existing) > 0
        and str(alert.get("id", "")).startswith("ALT-")
        and source != "stakeholder_submit"
    ):
        score = int(round(0.35 * score + 0.65 * int(existing)))

    if score >= 70:
        risk_level = "high"
    elif score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    attribution = sorted(
        [{"feature": k, "contribution": v} for k, v in features.items() if v > 0],
        key=lambda x: x["contribution"],
        reverse=True,
    )

    return {
        "model": "lowtrans-explainable-v1",
        "backend": "heuristic",
        "score": score,
        "risk_level": risk_level,
        "features": features,
        "attribution": attribution,
        "top_drivers": [a["feature"] for a in attribution[:3]],
        "summary": (
            f"ML score {score}/100 ({risk_level}). "
            + (
                "Top drivers: " + ", ".join(f"{a['feature']} (+{a['contribution']})" for a in attribution[:3])
                if attribution
                else "No elevated risk features."
            )
        ),
    }


def score_transaction(alert: dict[str, Any]) -> dict[str, Any]:
    """Prefer sklearn GB; fall back to weighted explainable scorer."""
    sk = predict_sklearn(alert)
    if sk:
        existing = alert.get("kyt_score")
        source = str(alert.get("source") or "")
        score = int(sk["score"])
        if (
            existing is not None
            and int(existing) > 0
            and str(alert.get("id", "")).startswith("ALT-")
            and source != "stakeholder_submit"
        ):
            score = int(round(0.55 * score + 0.45 * int(existing)))
        if score >= 70:
            risk_level = "high"
        elif score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"
        attribution = sk.get("attribution") or []
        return {
            **sk,
            "score": score,
            "risk_level": risk_level,
            "summary": (
                f"Sklearn GB score {score}/100 ({risk_level})"
                + (f", MAE≈{sk.get('mae')}" if sk.get("mae") is not None else "")
                + (
                    ". Top drivers: "
                    + ", ".join(f"{a['feature']} (+{a['contribution']})" for a in attribution[:3])
                    if attribution
                    else "."
                )
            ),
        }
    return _heuristic_score(alert)


def soft_decision_from_score(score: int, policy_hits: list[dict[str, Any]]) -> tuple[str, float, str]:
    """Propose CLEAR/REVIEW/ESCALATE before hard gates are applied."""
    if any(h.get("decision") == "ESCALATE" for h in policy_hits):
        return "ESCALATE", 0.9, "escalate_edd"
    if score >= 70:
        return "ESCALATE", 0.82, "escalate_edd"
    if score >= 40:
        return "REVIEW", 0.72, "analyst_review"
    return "CLEAR", 0.88, "auto_clear"
