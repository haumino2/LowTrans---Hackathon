"""Submit a new transaction → ML validate → create alert → optional investigate."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from agent.ml_scorer import score_transaction
from agent.orchestrator import run_workflow
from db.repository import load_alerts, save_alerts


def _write_scenario_graph(alert: dict[str, Any], scenario_id: str) -> None:
    """Persist an on-chain graph for a submitted scenario so the
    OnChain_Graph_Analyzer and Connections Graph tab have real data to show.
    Best-effort: never break submit if graph write fails."""
    try:
        from agent.scenarios import build_scenario_graph
        from agent.tools.graph_tools import GRAPHS_DIR

        graph = build_scenario_graph(scenario_id, alert)
        if not graph:
            return
        GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
        path = GRAPHS_DIR / f"{alert['id']}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2)
    except Exception:
        pass


def _next_alert_id(existing: list[dict[str, Any]]) -> str:
    nums = []
    for a in existing:
        aid = str(a.get("id", ""))
        if aid.startswith("ALT-"):
            try:
                nums.append(int(aid.split("-", 1)[1]))
            except ValueError:
                pass
    n = max(nums) + 1 if nums else 4001
    return f"ALT-{n}"


def build_alert_from_transaction(payload: dict[str, Any], existing: list[dict[str, Any]]) -> dict[str, Any]:
    """Normalize stakeholder-submitted tx into alert shape."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    customer_name = str(payload.get("customer_name") or "Walk-in Customer").strip()
    customer_id = str(payload.get("customer_id") or f"CUST-{uuid.uuid4().hex[:4].upper()}")
    amount = float(payload.get("amount_usd") or 0)
    direction = str(payload.get("direction") or "withdrawal").lower()
    asset = str(payload.get("asset") or "USDC").upper()
    network = str(payload.get("network") or "Ethereum")
    travel = str(payload.get("travel_rule_status") or "complete").lower()
    tags = list(payload.get("risk_tags") or [])
    signals = dict(payload.get("signals") or {})
    signals.setdefault("wallet_age_days", int(payload.get("account_age_days") or 30))
    signals.setdefault("mixer_exposure", "mixer_exposure" in tags or bool(payload.get("mixer_exposure")))
    signals.setdefault("pep_hit", bool(payload.get("pep_hit")))
    signals.setdefault("device_risk", str(payload.get("device_risk") or "low"))
    signals.setdefault("ip_country", str(payload.get("country") or "US"))

    counterparty = str(payload.get("counterparty") or "Unknown counterparty")
    # Real OFAC SDN screen when public list is cached; intake checkbox is OR'd in.
    ofac_hit = False
    ofac_score = 0.0
    ofac_matched = None
    ofac_program = None
    ofac_note = None
    list_sources = ["PEP World-Check (simulated)"]
    try:
        from agent.domain.sanctions import ofac_available, screen_ofac

        if ofac_available():
            ofac = screen_ofac(customer_name, counterparty)
            ofac_hit = bool(ofac.get("hit"))
            ofac_score = float(ofac.get("score") or 0.0)
            ofac_matched = ofac.get("matched_name")
            ofac_program = ofac.get("program")
            list_sources = ["OFAC SDN (public list)", "PEP World-Check (simulated)"]
            if ofac_hit and ofac_matched:
                ofac_note = (
                    f"OFAC SDN match: {ofac_matched}"
                    + (f" [{ofac_program}]" if ofac_program else "")
                    + f" (score={ofac_score:.0%})"
                )
            else:
                ofac_note = f"No OFAC SDN hit (best score {ofac_score:.0%})"
    except Exception:
        pass

    forced_hit = bool(payload.get("sanctions_hit"))
    signals["sanctions_hit"] = ofac_hit or forced_hit
    sanctions_status = "hit" if signals["sanctions_hit"] else ("review" if signals["pep_hit"] else "clear")
    if ofac_note:
        sanctions_note = ofac_note
        if forced_hit and not ofac_hit:
            sanctions_note += "; intake checkbox forced hit"
    else:
        sanctions_note = payload.get("sanctions_note") or (
            "Submitted transaction — OFAC hit flagged by intake"
            if signals["sanctions_hit"]
            else "Submitted transaction — lists clear at intake"
        )
    if ofac_hit and "sanctions_proximity" not in tags:
        tags.append("sanctions_proximity")

    draft = {
        "id": _next_alert_id(existing),
        "customer_id": customer_id,
        "customer_name": customer_name,
        "email": str(payload.get("email") or f"{customer_id.lower()}@example.com"),
        "partner": str(payload.get("partner") or "Summit Crypto Exchange"),
        "partner_id": str(payload.get("partner_id") or "185654"),
        "session_id": f"SES-{uuid.uuid4().hex[:8]}",
        "status": "pending",
        "asset": asset,
        "network": network,
        "amount_usd": amount,
        "direction": direction,
        "kyt_score": 0,  # filled by independent KYT in investigator (not ML)
        "risk_level": "low",
        "risk_tags": tags,
        "wallet_address": str(
            payload.get("wallet_address")
            or "0x" + uuid.uuid4().hex + uuid.uuid4().hex[:8]
        ),
        "counterparty": counterparty,
        "travel_rule_status": travel,
        "account_age_days": int(payload.get("account_age_days") or 30),
        "device_os": str(payload.get("device_os") or "Unknown"),
        "flow_type": str(payload.get("flow_type") or "Withdrawal Flow"),
        "country": str(payload.get("country") or "United States"),
        "state": str(payload.get("state") or ""),
        "address": str(payload.get("address") or ""),
        "zip": str(payload.get("zip") or ""),
        "phone": str(payload.get("phone") or ""),
        "connections": int(payload.get("connections") or 3),
        "created_at": now,
        "signals": signals,
        "rules_fired": list(payload.get("rules_fired") or []),
        "sanctions_screening": {
            "status": sanctions_status,
            "matches": 1 if signals["sanctions_hit"] else 0,
            "note": sanctions_note,
            "match_confidence": ofac_score if ofac_score else (0.91 if signals["sanctions_hit"] else 0.12),
            "matched_name": ofac_matched,
            "program": ofac_program,
            "list_sources": list_sources,
        },
        "crypto_details": {
            "chain": network,
            "confirmations": int(payload.get("confirmations") or 0),
            "tx_hash": payload.get("tx_hash") or f"0x{uuid.uuid4().hex}",
        },
        "source": "stakeholder_submit",
    }

    ml = score_transaction(draft)
    draft["risk_level"] = ml["risk_level"]
    draft["ml_score"] = ml
    # kyt_score stays 0 until investigator runs compute_kyt_score (independent of ML)
    # Auto-tag from top drivers
    for feat in ml.get("top_drivers") or []:
        if feat == "mixer_exposure" and "mixer_exposure" not in draft["risk_tags"]:
            draft["risk_tags"].append("mixer_exposure")
        if feat == "travel_rule_gap" and "travel_rule_missing" not in draft["risk_tags"] and travel == "missing":
            draft["risk_tags"].append("travel_rule_missing")
        if feat == "new_wallet" and "new_wallet" not in draft["risk_tags"]:
            draft["risk_tags"].append("new_wallet")
    return draft


def submit_transaction(
    payload: dict[str, Any],
    *,
    run_triage: bool = True,
) -> dict[str, Any]:
    alerts = load_alerts()
    alert = build_alert_from_transaction(payload, alerts)
    scenario_id = payload.get("scenario_id")
    if scenario_id:
        # Write the graph BEFORE triage so the investigator's on-chain step sees it.
        _write_scenario_graph(alert, str(scenario_id))
    triage_result = None
    if run_triage:
        triage_result = run_workflow(alert)
        alert["triage_result"] = triage_result
        decision = triage_result.get("decision", "REVIEW")
        alert["status"] = {
            "CLEAR": "clear",
            "REVIEW": "review",
            "ESCALATE": "escalate",
        }.get(decision, "review")
    alerts.append(alert)
    save_alerts(alerts)
    return {
        "ok": True,
        "alert": alert,
        "ml_score": alert.get("ml_score"),
        "triage_result": triage_result,
    }
