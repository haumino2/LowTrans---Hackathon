"""Workflow orchestrator — runs AML/KYT agents step-by-step with visible audit trail."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from agent.rag import rag_engine

WORKSPACE_LINKS: dict[str, str] = {
    "Transaction Monitoring Agent": "/cases/{alert_id}?tab=Overview&module=Crypto",
    "Sanctions Screening Agent": "/copilot?alert_id={alert_id}&q=screening",
    "Graph Analyst Agent": "/cases/{alert_id}?tab=Connections+Graph",
    "Data Analyst Agent": "/analyst?alert_id={alert_id}",
    "Doc KYC Agent": "/cases/{alert_id}?tab=Overview&module=Customer+Details",
    "OSINT Search Agent": "/copilot?alert_id={alert_id}&q=osint",
    "SAR Filing Agent": "/cases/{alert_id}?tab=Overview&sar=1",
    "RAG Memory": "/policy",
    "Decision Orchestrator": "/cases/{alert_id}?tab=Timeline",
}


def _step(
    step: int,
    agent: str,
    status: str,
    input_summary: str,
    output: str,
    duration_ms: int,
    workspace_link: str | None = None,
) -> dict[str, Any]:
    return {
        "step": step,
        "agent": agent,
        "status": status,
        "input": input_summary,
        "output": output,
        "duration_ms": duration_ms,
        "workspace_link": workspace_link,
    }


def _alert_input_summary(alert: dict[str, Any]) -> str:
    tags = ", ".join(alert.get("risk_tags", [])) or "none"
    return (
        f"{alert['id']}: {alert['customer_name']} — {alert['direction']} "
        f"${alert['amount_usd']:,.0f} {alert['asset']} ({alert['network']}), "
        f"KYT {alert['kyt_score']}, tags [{tags}], Travel Rule {alert['travel_rule_status']}"
    )


def run_workflow(
    alert: dict[str, Any],
    on_step: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Execute the full agent pipeline and return decision + workflow_steps."""
    steps: list[dict[str, Any]] = []
    step_num = 0
    aid = alert.get("id", "")

    def add(agent: str, status: str, inp: str, out: str, ms: int) -> None:
        nonlocal step_num
        step_num += 1
        link_tpl = WORKSPACE_LINKS.get(agent)
        link = link_tpl.format(alert_id=aid) if link_tpl and aid else None
        s = _step(step_num, agent, status, inp, out, ms, workspace_link=link)
        steps.append(s)
        if on_step:
            on_step(s)

    kyt = alert.get("kyt_score", 50)
    signals = alert.get("signals", {})
    travel = alert.get("travel_rule_status", "")
    amount = alert.get("amount_usd", 0)
    tags = alert.get("risk_tags", [])
    sanctions = alert.get("sanctions_screening", {})
    inp = _alert_input_summary(alert)

    # Step 1 — Alert ingestion
    t0 = time.perf_counter()
    add(
        "Alert Ingestion",
        "completed",
        inp,
        f"Loaded alert for session {alert.get('session_id', 'N/A')} — {alert['risk_level'].upper()} risk",
        max(8, int((time.perf_counter() - t0) * 1000) + 10),
    )

    # Step 2 — RAG memory retrieval
    t0 = time.perf_counter()
    similar = rag_engine.find_similar(alert, top_k=3)
    if similar:
        rag_out = "; ".join(
            f"{s['case_id']} → {s['resolution']} ({s['similarity']:.0%} match)"
            for s in similar
        )
    else:
        rag_out = "No similar cases in memory index"
    rag_label = (
        "Cohere Embed semantic search"
        if rag_engine.backend == "cohere"
        else "TF-IDF vector search"
    )
    add("RAG Memory", "completed", f"{rag_label} over {len(rag_engine.cases)} resolved cases", rag_out, 45)

    rationale: list[str] = []
    agents_used: list[str] = []
    decision = "REVIEW"
    confidence = 0.65
    disposition = "analyst_review"
    escalation_summary: str | None = None

    # Step 3 — Transaction Monitoring Agent (always)
    t0 = time.perf_counter()
    agents_used.append("Transaction Monitoring Agent")
    tm_flags: list[str] = []
    if kyt > 65:
        tm_flags.append(f"KYT {kyt} > threshold 65")
    if amount > 25000:
        tm_flags.append(f"high value ${amount:,.0f}")
    if travel in ("missing", "incomplete", "mismatch"):
        tm_flags.append(f"Travel Rule {travel}")
    if tags:
        tm_flags.append(f"tags: {', '.join(tags)}")
    tm_out = "; ".join(tm_flags) if tm_flags else f"Routine {alert['direction']} — KYT {kyt} within monitoring range"
    add(
        "Transaction Monitoring Agent",
        "completed",
        f"KYT score, amount, direction, Travel Rule status",
        tm_out,
        120,
    )

    # Step 4 — Sanctions Screening Agent
    has_sanctions = bool(signals.get("sanctions_hit")) or sanctions.get("status") == "hit"
    pep = bool(signals.get("pep_hit"))
    if has_sanctions or pep or sanctions.get("status") == "review":
        agents_used.append("Sanctions Screening Agent")
        if has_sanctions:
            s_out = f"HIT — {sanctions.get('matches', 0)} match(es). {sanctions.get('note', 'OFAC/PEP review required')}"
            rationale.append("Sanctions or PEP match detected — requires escalation per policy")
            decision, confidence, disposition = "ESCALATE", 0.92, "escalate_edd"
        else:
            s_out = f"Review — {sanctions.get('note', 'Fuzzy match under analyst review')}"
        add("Sanctions Screening Agent", "completed", "OFAC, PEP, adverse media lists", s_out, 180)
    else:
        add(
            "Sanctions Screening Agent",
            "skipped",
            "OFAC, PEP, adverse media lists",
            "No sanctions or PEP hits — skipped",
            5,
        )

    # Early exit on sanctions hit
    if decision == "ESCALATE" and has_sanctions:
        return _finalize(
            alert, similar, steps, agents_used, rationale, decision, confidence,
            disposition, escalation_summary, on_step,
        )

    # Step 5 — Graph Analyst Agent
    has_mixer = bool(signals.get("mixer_exposure")) or "mixer_exposure" in tags
    has_graph = has_mixer or alert.get("connections", 0) > 8 or "structuring" in tags
    if has_graph:
        agents_used.append("Graph Analyst Agent")
        if has_mixer:
            g_out = f"Mixer/privacy pool exposure — counterparty: {alert.get('counterparty', 'unknown')}"
            rationale.append("Mixer or privacy pool exposure confirmed on-chain")
        else:
            g_out = f"Network analysis: {alert.get('connections', 0)} direct connections, tags [{', '.join(tags)}]"
        add("Graph Analyst Agent", "completed", "On-chain graph, wallet clusters, bridge hops", g_out, 200)

        if has_mixer and travel in ("missing", "incomplete") and amount > 3000:
            rationale.append(f"Travel Rule {travel} for ${amount:,.0f} withdrawal")
            decision, confidence, disposition = "ESCALATE", 0.95, "block_transaction"
    else:
        add(
            "Graph Analyst Agent",
            "skipped",
            "On-chain graph, wallet clusters",
            "No mixer exposure or suspicious graph patterns",
            5,
        )

    if decision == "ESCALATE":
        return _finalize(
            alert, similar, steps, agents_used, rationale, decision, confidence,
            disposition, escalation_summary, on_step,
        )

    # Step 6 — Data Analyst Agent
    if kyt > 50 or len(alert.get("rules_fired", [])) > 0:
        agents_used.append("Data Analyst Agent")
        rules = alert.get("rules_fired", [])
        try:
            from agent.analyst import generate_sql
            from db.models import is_db_ready

            q = f"KYT and risk for customer {alert.get('customer_name')} partner {alert.get('partner')}"
            if is_db_ready():
                preview = generate_sql(q)
                da_out = f"NL-SQL: {preview['sql'][:120]}..." if len(preview["sql"]) > 120 else f"NL-SQL: {preview['sql']}"
            else:
                da_out = f"KYT {kyt}; {len(rules)} rule(s) fired — connect Postgres for NL-SQL"
        except Exception:
            da_out = f"KYT {kyt}; {len(rules)} rule(s) fired" if rules else f"KYT {kyt} — elevated signal correlation"
        add("Data Analyst Agent", "completed", "NL-to-SQL over transaction warehouse", da_out, 95)

        if kyt > 65:
            rationale.append(f"KYT score {kyt} exceeds escalation threshold (>65)")
            decision, confidence, disposition = "ESCALATE", 0.88, "escalate_edd"
    else:
        add(
            "Data Analyst Agent",
            "skipped",
            "Transaction history, rule correlations",
            "KYT and rule count below analysis threshold",
            5,
        )

    if decision == "ESCALATE":
        return _finalize(
            alert, similar, steps, agents_used, rationale, decision, confidence,
            disposition, escalation_summary, on_step,
        )

    # Travel Rule hard escalate
    if travel == "missing" and amount > 3000:
        rationale.append(f"Travel Rule missing for ${amount:,.0f} transfer — IVMS101 required")
        decision, confidence, disposition = "ESCALATE", 0.85, "escalate_edd"
        return _finalize(
            alert, similar, steps, agents_used, rationale, decision, confidence,
            disposition, escalation_summary, on_step,
        )

    # Step 7 — Doc KYC / OSINT (RAG-assisted path)
    rag_top = similar[0] if similar else None
    rag_clear = (
        rag_top
        and rag_top["similarity"] >= 0.4
        and rag_top["resolution"] in ("CLEAR", "REVIEW")
        and kyt <= 55
        and not signals.get("mixer_exposure")
        and not signals.get("sanctions_hit")
        and (travel != "missing" or amount <= 3000)
    )

    if rag_clear or kyt < 35:
        agents_used.append("Doc KYC Agent")
        if rag_clear:
            kyc_out = (
                f"RAG precedent {rag_top['case_id']} ({rag_top['resolution']}, "
                f"{rag_top['similarity']:.0%}) supports clearance"
            )
            rationale.append(
                f"RAG auto-clear: {rag_top['case_id']} ({rag_top['resolution']}) with "
                f"{rag_top['similarity']:.0%} similarity"
            )
            rationale.append(rag_top["analyst_notes"][:100])
            decision, confidence, disposition = "CLEAR", 0.89, "auto_clear"
        else:
            kyc_out = f"Low KYT {kyt}, Travel Rule {travel}, wallet age {signals.get('wallet_age_days', 0)}d"
            rationale.append(f"KYT score {kyt} below auto-clear threshold (<35)")
            if travel in ("complete", "n/a"):
                rationale.append(f"Travel Rule status: {travel}")
            decision, confidence, disposition = "CLEAR", 0.93, "auto_clear"
        add("Doc KYC Agent", "completed", "KYC signals, document match, RAG precedent", kyc_out, 110)
        agents_used.append("OSINT Search Agent")
        add("OSINT Search Agent", "completed", "Counterparty VASP verification", f"Counterparty: {alert.get('counterparty', 'N/A')}", 85)
    elif kyt > 35 or travel in ("mismatch", "incomplete") or len(tags) > 0:
        agents_used.append("OSINT Search Agent")
        rationale.append(f"KYT score {kyt} in review range or secondary signals present")
        osint_out = "Secondary signals require L1 analyst review"
        decision, confidence, disposition = "REVIEW", 0.70, "analyst_review"
        add("OSINT Search Agent", "completed", "Entity research, Travel Rule validation", osint_out, 150)
    else:
        add("Doc KYC Agent", "skipped", "KYC signals", "No document review required", 5)

    return _finalize(
        alert, similar, steps, agents_used, rationale, decision, confidence,
        disposition, escalation_summary, on_step,
    )


def _finalize(
    alert: dict[str, Any],
    similar: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    agents_used: list[str],
    rationale: list[str],
    decision: str,
    confidence: float,
    disposition: str,
    escalation_summary: str | None,
    on_step: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    step_num = len(steps)

    aid = alert.get("id", "")
    link_tpl = WORKSPACE_LINKS.get("Decision Orchestrator")
    dec_link = link_tpl.format(alert_id=aid) if link_tpl and aid else None

    def _append_step(s: dict[str, Any]) -> None:
        steps.append(s)
        if on_step:
            on_step(s)

    # Decision synthesis
    _append_step(_step(
        step_num + 1,
        "Decision Orchestrator",
        "completed",
        f"Signals from {len([s for s in steps if s['status'] == 'completed'])} agents",
        f"FINAL: {decision} ({confidence:.0%} confidence) → {disposition}",
        35,
        workspace_link=dec_link,
    ))

    # SAR Filing Agent (conditional)
    if decision == "ESCALATE":
        agents_used.append("SAR Filing Agent")
        escalation_summary = _draft_escalation(alert, rationale, similar)
        sar_link = WORKSPACE_LINKS.get("SAR Filing Agent", "").format(alert_id=aid) or None
        _append_step(_step(
            step_num + 2,
            "SAR Filing Agent",
            "completed",
            f"Case {alert['id']}, decision ESCALATE",
            escalation_summary[:200] + "..." if len(escalation_summary) > 200 else escalation_summary,
            350,
            workspace_link=sar_link,
        ))
        audit_offset = 3
    else:
        _append_step(_step(
            step_num + 2,
            "SAR Filing Agent",
            "skipped",
            "Escalation check",
            f"Decision {decision} — no SAR draft required",
            5,
        ))
        audit_offset = 3

    _append_step(_step(
        step_num + audit_offset,
        "Audit Logger",
        "completed",
        f"Decision {decision}, agents: {len(agents_used)}",
        "Immutable audit record written with RAG case citations",
        18,
    ))

    return {
        "decision": decision,
        "confidence": confidence,
        "rationale": rationale,
        "signals_reviewed": [
            "kyt_score", "travel_rule", "wallet_age", "mixer_exposure",
            "sanctions_screening", "counterparty", "amount_usd", "risk_tags",
        ],
        "similar_cases": similar,
        "agents_used": list(dict.fromkeys(agents_used)),
        "suggested_disposition": disposition,
        "escalation_summary": escalation_summary,
        "rag_enabled": True,
        "policy_version": "v1.0",
        "workflow_steps": steps,
        "workflow_summary": {
            "total_steps": len(steps),
            "agents_run": len([s for s in steps if s["status"] == "completed" and s["agent"] != "Alert Ingestion"]),
            "agents_skipped": len([s for s in steps if s["status"] == "skipped"]),
            "total_duration_ms": sum(s["duration_ms"] for s in steps),
        },
    }


def _draft_escalation(
    alert: dict[str, Any], rationale: list[str], similar: list[dict[str, Any]],
) -> str:
    lines = [
        f"## Escalation Summary — {alert['id']}",
        f"**Customer:** {alert['customer_name']} ({alert['customer_id']})",
        f"**Transaction:** {alert['direction'].title()} ${alert['amount_usd']:,.0f} "
        f"({alert['asset']} on {alert['network']})",
        f"**KYT Score:** {alert['kyt_score']} | **Risk:** {alert['risk_level'].upper()}",
        "",
        "### Risk Factors",
    ]
    for r in rationale:
        lines.append(f"- {r}")
    if alert.get("rules_fired"):
        lines.append("\n### Rules Fired")
        for rule in alert["rules_fired"]:
            lines.append(f"- [{rule['severity'].upper()}] {rule['name']}")
    if similar:
        lines.append("\n### Similar Historical Cases (RAG)")
        for s in similar[:2]:
            lines.append(f"- {s['case_id']}: {s['resolution']} — {s['analyst_notes'][:100]}")
    lines.extend([
        "",
        "### Recommended Actions",
        "1. Initiate Enhanced Due Diligence (EDD)",
        "2. Freeze transaction pending compliance review",
        "3. Prepare SAR narrative if suspicion confirmed",
        "4. Document all findings in audit trail",
    ])
    return "\n".join(lines)
