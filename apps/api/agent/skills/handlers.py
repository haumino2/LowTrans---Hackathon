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
from agent.tools.graph_tools import summarize_graph
from agent.tools.rag_tools import find_similar_cases
from db.repository import get_alert

Handler = Callable[[str, str | None], dict[str, Any]]


def _card(title: str, card_type: str, fields: list[dict[str, str]]) -> dict[str, Any]:
    return {"type": card_type, "title": title, "fields": fields}


def handle_analyst_nl_sql(message: str, alert_id: str | None) -> dict[str, Any]:
    analysis = analyze_question(message)
    if analysis.get("error") and not analysis.get("columns"):
        return {"type": "error", "reply": analysis["error"], "cards": []}
    viz = analysis["visualization"]
    return {
        "type": "visualization",
        "reply": viz["summary"],
        "visualization": viz,
        "cards": [
            _card(
                "Query Result",
                "metrics",
                [
                    {"label": "Rows", "value": str(viz["row_count"])},
                    {"label": "Chart", "value": viz["chart_type"]},
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
    g = summarize_graph(alert_id)
    cards = [
        _card(
            "Link Analysis",
            "graph",
            [
                {"label": "Nodes", "value": str(g["node_count"])},
                {"label": "Flagged", "value": str(len(g["flagged_node_ids"]))},
            ],
        )
    ]
    return {
        "type": "graph",
        "reply": g["summary"],
        "cards": cards,
        "flagged_node_ids": g["flagged_node_ids"],
        "graph": g.get("graph"),
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
}


def dispatch_skill(skill_id: str, message: str, alert_id: str | None = None) -> dict[str, Any]:
    handler = SKILL_HANDLERS.get(skill_id, handle_policy_qa)
    return handler(message, alert_id)
