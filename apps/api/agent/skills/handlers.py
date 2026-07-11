"""Skill handlers — registry dispatches skill_id → handler."""

from __future__ import annotations

from typing import Any, Callable

from agent.analyst import analyze_question
from agent.bedrock import health_check as bedrock_health
from agent.bedrock import is_configured, safe_invoke
from agent.domain.packs import (
    kyb_due_diligence,
    osint_research,
    rule_assistant_suggest,
    screening_with_policy_overlay,
)
from agent.tools.case_tools import read_policy
from agent.tools.rag_tools import find_similar_cases
from db.repository import get_alert

Handler = Callable[[str, str | None], dict[str, Any]]


def _card(title: str, card_type: str, fields: list[dict[str, str]]) -> dict[str, Any]:
    return {"type": card_type, "title": title, "fields": fields}


def handle_analyst_nl_sql(message: str, alert_id: str | None) -> dict[str, Any]:
    analysis = analyze_question(message)
    if analysis.get("error") and not analysis.get("visualization"):
        return {
            "type": "error",
            "reply": analysis.get("error") or "Analyst query failed",
            "cards": [],
        }
    viz = analysis.get("visualization")
    if not viz:
        return {
            "type": "error",
            "reply": analysis.get("error") or analysis.get("explanation") or "No visualization produced",
            "cards": [],
        }
    return {
        "type": "visualization",
        "reply": viz.get("summary", "Query complete"),
        "visualization": viz,
        "cards": [
            _card(
                "Query Result",
                "metrics",
                [
                    {"label": "Rows", "value": str(viz.get("row_count", 0))},
                    {"label": "Chart", "value": str(viz.get("chart_type", "table"))},
                ],
            )
        ],
    }


def handle_rag_lookup(message: str, alert_id: str | None) -> dict[str, Any]:
    if alert_id:
        alert = get_alert(alert_id)
        if alert:
            similar = find_similar_cases(alert, top_k=3)
            lines = [
                f"- {s['case_id']} — {s['resolution']} ({s['similarity']:.0%}): {s['analyst_notes'][:100]}"
                for s in similar
            ]
            cards = [
                _card(
                    c["case_id"],
                    "case",
                    [
                        {"label": "Resolution", "value": c["resolution"]},
                        {"label": "Match", "value": f"{c['similarity']:.0%}"},
                    ],
                )
                for c in similar
            ]
            return {
                "type": "rag",
                "reply": "Similar resolved cases:\n" + "\n".join(lines),
                "cases": similar,
                "cards": cards,
            }
    return {
        "type": "rag",
        "reply": "Open a case for targeted RAG lookup, or ask about policy thresholds.",
        "cards": [],
    }


def handle_policy_qa(message: str, alert_id: str | None) -> dict[str, Any]:
    policy = read_policy()[:4000]
    if is_configured():
        model_id = bedrock_health(live=False).get("model_id")
        reply = safe_invoke(
            message,
            system=(
                "You are LowTrans AML Copilot. Answer using ONLY the policy below. "
                "Be concise.\n\n" + policy
            ),
            fallback="Policy Q&A requires Bedrock. See Policy page.",
        )
    else:
        model_id = None
        reply = "Bedrock not configured. Open Policy & RAG for full policy text."
    return {
        "type": "text",
        "reply": reply,
        "model_id": model_id,
        "cards": [_card("Active Policy", "policy", [{"label": "Version", "value": "v1.0"}])],
    }


def handle_sar_draft(message: str, alert_id: str | None) -> dict[str, Any]:
    if not alert_id:
        return {"type": "sar", "reply": "Open a case to draft SAR narrative.", "cards": []}
    alert = get_alert(alert_id)
    if not alert:
        return {"type": "error", "reply": "Alert not found", "cards": []}
    ctx = (
        f"Customer: {alert['customer_name']}, KYT: {alert['kyt_score']}, "
        f"Amount: ${alert['amount_usd']}, Tags: {alert.get('risk_tags')}"
    )
    if is_configured():
        model_id = bedrock_health(live=False).get("model_id")
        reply = safe_invoke(
            f"Draft SAR narrative opening:\n{ctx}\n\nNote: {message}",
            system="You are a SAR Filing Agent for a crypto VASP. Professional SAR narrative.",
            fallback="SAR draft unavailable — Bedrock throttled.",
        )
    else:
        model_id = None
        reply = f"SAR draft (template): Escalation recommended for {alert['customer_name']} — {ctx}"
    return {
        "type": "sar",
        "reply": reply,
        "model_id": model_id,
        "cards": [
            _card(
                "Filing Recommendation",
                "sar",
                [
                    {"label": "Case", "value": alert_id},
                    {"label": "KYT", "value": str(alert["kyt_score"])},
                    {"label": "Action", "value": "Proceed with SAR consideration"},
                ],
            )
        ],
    }


def handle_sanctions_check(message: str, alert_id: str | None) -> dict[str, Any]:
    if not alert_id:
        return {"type": "text", "reply": "Provide alert context for screening.", "cards": []}
    countries = []
    lower = message.lower()
    for code in ("af", "kp", "ir", "sy", "ru"):
        if code in lower or code.upper() in message:
            countries.append(code.upper())
    result = screening_with_policy_overlay(alert_id, message, countries or None)
    return {**result, "type": "screening"}


def handle_graph_summary(message: str, alert_id: str | None) -> dict[str, Any]:
    if not alert_id:
        return {"type": "text", "reply": "Open a case for link analysis.", "cards": []}
    # Same on-chain exposure engine as supervisor (compute_exposure), not a divergent summary.
    from agent.tools.graph_tools import compute_exposure, summarize_graph

    exposure = compute_exposure(alert_id)
    g = summarize_graph(alert_id)
    reply = exposure.get("summary") or g.get("summary") or "Graph analysis complete."
    cards = [
        _card(
            "Link Analysis",
            "graph",
            [
                {"label": "Nodes", "value": str(g.get("node_count", 0))},
                {"label": "Flagged", "value": str(len(g.get("flagged_node_ids") or []))},
                {"label": "Direct exposure", "value": f"${exposure.get('direct_exposure', 0):,.0f}"},
                {"label": "Indirect exposure", "value": f"${exposure.get('indirect_exposure', 0):,.0f}"},
            ],
        )
    ]
    return {
        "type": "graph",
        "reply": reply,
        "cards": cards,
        "flagged_node_ids": g.get("flagged_node_ids") or [],
        "graph": g.get("graph"),
        "exposure": exposure,
    }


def handle_kyt_score(message: str, alert_id: str | None) -> dict[str, Any]:
    if not alert_id:
        return {"type": "text", "reply": "Open a case for KYT analysis.", "cards": []}
    alert = get_alert(alert_id)
    if not alert:
        return {"type": "error", "reply": "Alert not found", "cards": []}
    return {
        "type": "alert_summary",
        "reply": (
            f"KYT **{alert['kyt_score']}** ({alert['risk_level']}). "
            f"Tags: {', '.join(alert.get('risk_tags', []))}"
        ),
        "cards": [
            _card(
                "KYT Analysis",
                "metrics",
                [
                    {"label": "Score", "value": str(alert["kyt_score"])},
                    {"label": "Travel Rule", "value": alert.get("travel_rule_status", "—")},
                ],
            )
        ],
    }


def handle_osint_research(message: str, alert_id: str | None) -> dict[str, Any]:
    name = message.replace("analyze", "").replace("research", "").strip() or ""
    result = osint_research(name, alert_id)
    return {**result, "type": "osint"}


def handle_kyb_verify(message: str, alert_id: str | None) -> dict[str, Any]:
    if not alert_id:
        return {"type": "text", "reply": "Open a case for KYB review.", "cards": []}
    result = kyb_due_diligence(alert_id)
    return {**result, "type": "kyb"}


def handle_rule_build(message: str, alert_id: str | None) -> dict[str, Any]:
    result = rule_assistant_suggest(message)
    return {**result, "type": "rule"}


def handle_rule_fire_rates(message: str, alert_id: str | None) -> dict[str, Any]:
    return handle_analyst_nl_sql("rule fire rate by risk level " + message, alert_id)


def handle_ml_validate(message: str, alert_id: str | None) -> dict[str, Any]:
    from agent.ml_scorer import score_transaction

    if not alert_id:
        return {"type": "text", "reply": "Open a case or submit a transaction for ML validation.", "cards": []}
    alert = get_alert(alert_id)
    if not alert:
        return {"type": "error", "reply": "Alert not found", "cards": []}
    ml = score_transaction(alert)
    fields = [
        {"label": "Score", "value": f"{ml['score']}/100"},
        {"label": "Risk", "value": str(ml["risk_level"]).upper()},
        {"label": "Model", "value": ml["model"]},
    ]
    for a in ml.get("attribution", [])[:4]:
        fields.append({"label": a["feature"], "value": f"+{a['contribution']}"})
    return {
        "type": "ml_score",
        "reply": ml["summary"],
        "ml_score": ml,
        "cards": [_card("ML Transaction Validator", "metrics", fields)],
    }


def handle_ubo_unroll(message: str, alert_id: str | None) -> dict[str, Any]:
    from agent.domain.ubo import unroll_ubo

    alert = get_alert(alert_id) if alert_id else None
    name = (alert or {}).get("customer_name") or message.strip() or "Unknown"
    ubo = unroll_ubo(str(name), alert)
    fields = [
        {"label": "Depth", "value": str(ubo["depth"])},
        {"label": "High-risk nodes", "value": str(len(ubo.get("high_risk_nodes") or []))},
        {"label": "Source", "value": ubo.get("source", "mock:ubo")},
    ]
    for n in (ubo.get("high_risk_nodes") or [])[:3]:
        fields.append({"label": n["name"], "value": f"{n.get('risk')} @ depth {n.get('depth')}"})
    return {
        "type": "ubo",
        "reply": ubo["summary"],
        "ubo": ubo,
        "cards": [_card("UBO Unroller", "business", fields)],
    }


def handle_device_ip_check(message: str, alert_id: str | None) -> dict[str, Any]:
    if not alert_id:
        return {"type": "text", "reply": "Open a case for device/IP check.", "cards": []}
    alert = get_alert(alert_id)
    if not alert:
        return {"type": "error", "reply": "Alert not found", "cards": []}
    signals = alert.get("signals") or {}
    return {
        "type": "device",
        "reply": (
            f"Device risk **{signals.get('device_risk', 'low')}**; "
            f"IP {signals.get('ip_country', alert.get('country'))}; OS {alert.get('device_os', '—')}."
        ),
        "cards": [
            _card(
                "Device & IP",
                "metrics",
                [
                    {"label": "Device risk", "value": str(signals.get("device_risk", "low"))},
                    {"label": "IP country", "value": str(signals.get("ip_country", alert.get("country", "—")))},
                    {"label": "OS", "value": str(alert.get("device_os", "—"))},
                ],
            )
        ],
    }


def handle_behavioral_patterns(message: str, alert_id: str | None) -> dict[str, Any]:
    from agent.domain.behavioral import analyze_behavior

    alert = get_alert(alert_id) if alert_id else None
    if not alert:
        return {"type": "text", "reply": "Open a case for behavioral analysis.", "cards": []}
    behavior = analyze_behavior(alert)
    fields = [{"label": "Patterns", "value": str(len(behavior.get("patterns") or []))}]
    for p in behavior.get("patterns") or []:
        fields.append({"label": p["name"], "value": p["severity"]})
    return {
        "type": "behavioral",
        "reply": behavior["summary"],
        "behavioral": behavior,
        "cards": [_card("Behavioral Patterns", "metrics", fields)],
    }


def handle_fiat_crypto_bridge(message: str, alert_id: str | None) -> dict[str, Any]:
    from agent.domain.fiat_bridge import trace_bridge

    alert = get_alert(alert_id) if alert_id else None
    if not alert:
        return {"type": "text", "reply": "Open a case for bridge tracing.", "cards": []}
    bridge = trace_bridge(alert)
    fields = [
        {"label": "Partner", "value": str(bridge.get("partner"))},
        {"label": "Latency", "value": f"~{bridge.get('latency_hours_est')}h"},
        {"label": "Legs", "value": str(len(bridge.get("legs") or []))},
    ]
    return {
        "type": "bridge",
        "reply": bridge["summary"],
        "bridge": bridge,
        "cards": [_card("Fiat-Crypto Bridge", "metrics", fields)],
    }


def handle_intake_parse(message: str, alert_id: str | None) -> dict[str, Any]:
    alert = get_alert(alert_id) if alert_id else None
    if not alert:
        return {"type": "text", "reply": "Provide an alert_id to parse intake.", "cards": []}
    return {
        "type": "intake",
        "reply": f"Intake normalized for **{alert['id']}** — {alert.get('customer_name')}, ${alert.get('amount_usd'):,.0f}.",
        "cards": [],
    }


def handle_sla_priority(message: str, alert_id: str | None) -> dict[str, Any]:
    from agent.ml_scorer import score_transaction

    alert = get_alert(alert_id) if alert_id else None
    if not alert:
        return {"type": "text", "reply": "Open a case for SLA prioritization.", "cards": []}
    ml = score_transaction(alert)
    bucket = "fast-track" if ml["score"] >= 70 else ("elevated" if ml["score"] >= 40 else "routine")
    return {
        "type": "sla",
        "reply": f"SLA bucket **{bucket}** based on ML {ml['score']}/100.",
        "cards": [_card("SLA & Priority", "metrics", [{"label": "Bucket", "value": bucket}, {"label": "ML", "value": str(ml["score"])}])],
    }


def handle_adaptive_router(message: str, alert_id: str | None) -> dict[str, Any]:
    from agent.ml_scorer import score_transaction
    from agent.policy_gates import evaluate_hard_gates
    from agent.supervisor import ROUTE_LABELS, choose_investigation_route

    alert = get_alert(alert_id) if alert_id else None
    if not alert:
        return {"type": "text", "reply": "Open a case for adaptive routing.", "cards": []}
    ml = score_transaction(alert)
    hits = evaluate_hard_gates(alert)
    route, reason = choose_investigation_route(alert, ml, hits)
    label = ROUTE_LABELS.get(route, route)
    return {
        "type": "route",
        "reply": f"**{label}** — {reason}",
        "cards": [
            _card(
                "Adaptive Router",
                "metrics",
                [
                    {"label": "Route", "value": label},
                    {"label": "ML", "value": str(ml.get("score"))},
                ],
            )
        ],
    }


def handle_context_retrieve(message: str, alert_id: str | None) -> dict[str, Any]:
    return handle_rag_lookup(message or "similar cases", alert_id)


def handle_confidence_score(message: str, alert_id: str | None) -> dict[str, Any]:
    alert = get_alert(alert_id) if alert_id else None
    tr = (alert or {}).get("triage_result") or {}
    conf = tr.get("confidence", 0.7)
    return {
        "type": "confidence",
        "reply": f"Confidence **{float(conf):.0%}** for decision {tr.get('decision', 'pending')}.",
        "cards": [],
    }


def handle_audit_compile(message: str, alert_id: str | None) -> dict[str, Any]:
    alert = get_alert(alert_id) if alert_id else None
    tr = (alert or {}).get("triage_result") or {}
    pack = tr.get("audit_pack") or {}
    return {
        "type": "audit",
        "reply": (
            f"Audit pack ready for **{alert_id}**: decision {pack.get('decision') or tr.get('decision', '—')}, "
            f"{len(pack.get('rationale') or tr.get('rationale') or [])} rationale lines."
        ),
        "cards": [],
        "audit_pack": pack,
    }


SKILL_HANDLERS: dict[str, Handler] = {
    "analyst-nl-sql": handle_analyst_nl_sql,
    "rag-lookup": handle_rag_lookup,
    "policy-qa": handle_policy_qa,
    "sar-draft": handle_sar_draft,
    "sanctions-check": handle_sanctions_check,
    "graph-summary": handle_graph_summary,
    "kyt-score": handle_kyt_score,
    "travel-rule-check": handle_kyt_score,
    "osint-research": handle_osint_research,
    "kyb-verify": handle_kyb_verify,
    "rule-build": handle_rule_build,
    "rule-fire-rates": handle_rule_fire_rates,
    "ml-validate": handle_ml_validate,
    "ubo-unroll": handle_ubo_unroll,
    "device-ip-check": handle_device_ip_check,
    "behavioral-patterns": handle_behavioral_patterns,
    "fiat-crypto-bridge": handle_fiat_crypto_bridge,
    "intake-parse": handle_intake_parse,
    "sla-priority": handle_sla_priority,
    "adaptive-router": handle_adaptive_router,
    "context-retrieve": handle_context_retrieve,
    "confidence-score": handle_confidence_score,
    "audit-compile": handle_audit_compile,
}


def dispatch_skill(skill_id: str, message: str, alert_id: str | None = None) -> dict[str, Any]:
    handler = SKILL_HANDLERS.get(skill_id, handle_policy_qa)
    return handler(message, alert_id)
