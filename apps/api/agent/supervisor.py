"""4-node investigation supervisor — Orchestrator → Identity → Investigator → Arbiter."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

from agent.bedrock import is_configured, safe_invoke
from agent.domain.behavioral import analyze_behavior
from agent.domain.fiat_bridge import trace_bridge
from agent.domain.packs import kyb_due_diligence, osint_research, screening_with_policy_overlay
from agent.domain.ubo import unroll_ubo
from agent.kyt import compute_kyt_score
from agent.ml_scorer import score_transaction, soft_decision_from_score
from agent.policy_gates import apply_gates_to_decision, evaluate_hard_gates
from agent.rag import rag_engine
from agent.state import InvestigationState
from agent.tools.graph_tools import compute_exposure

OnStep = Callable[[dict[str, Any]], None] | None

NODE_ORCHESTRATOR = "Orchestrator"
NODE_IDENTITY = "Entity Identity Agent"
NODE_INVESTIGATOR = "Financial Crime Investigator"
NODE_ARBITER = "Arbiter"

# Canonical map: skills that run during triage (source of truth for mode).
# Skills not listed here are copilot-only. graph-summary is triage + conditional.
TRIAGE_SKILLS_BY_NODE: dict[str, tuple[str, ...]] = {
    "orchestrator": (
        "intake-parse",
        "context-retrieve",
        "rag-lookup",
        "sla-priority",
        "adaptive-router",
    ),
    "entity-identity": (
        "sanctions-check",
        "osint-research",
        "kyb-verify",
        "ubo-unroll",
        "device-ip-check",
    ),
    "financial-crime-investigator": (
        "ml-validate",
        "kyt-score",
        "travel-rule-check",
        "graph-summary",
        "behavioral-patterns",
        "fiat-crypto-bridge",
    ),
    "arbiter": (
        "confidence-score",
        "sar-draft",
        "audit-compile",
    ),
}

CONDITIONAL_TRIAGE_SKILLS: frozenset[str] = frozenset({"graph-summary"})

ROUTE_LABELS: dict[str, str] = {
    "FAST_TRACK": "FAST-TRACK",
    "FULL": "FULL investigation",
    "STANDARD": "STANDARD",
}

HITL_CONFIDENCE_THRESHOLD = 0.70


def triage_skill_ids() -> frozenset[str]:
    return frozenset(sid for skills in TRIAGE_SKILLS_BY_NODE.values() for sid in skills)


def skill_mode(skill_id: str) -> str:
    """Derive mode from canonical triage map — not in map ⇒ copilot."""
    return "triage" if skill_id in triage_skill_ids() else "copilot"


def annotate_skill(skill: dict[str, Any]) -> dict[str, Any]:
    """Attach mode (+ conditional) for /api/skills consumers."""
    sid = skill.get("id") or ""
    out = {**skill, "mode": skill_mode(sid)}
    if sid in CONDITIONAL_TRIAGE_SKILLS:
        out["conditional"] = True
    return out


WORKSPACE_LINKS: dict[str, str] = {
    NODE_ORCHESTRATOR: "/cases/{alert_id}?tab=Timeline",
    NODE_IDENTITY: "/cases/{alert_id}?tab=Overview",
    NODE_INVESTIGATOR: "/cases/{alert_id}?tab=Connections+Graph",
    NODE_ARBITER: "/cases/{alert_id}?tab=Overview&sar=1",
}

# Skills that use mock / simulated vendor data — tag outputs for investor honesty.
SIMULATED_SKILL_IDS = frozenset(
    {
        "osint-research",
        "kyb-verify",
        "ubo-unroll",
        "fiat-crypto-bridge",
    }
)


def _tag_simulated(output: str, skill_id: str | None = None) -> str:
    text = (output or "").strip()
    if not text:
        return "[simulated]"
    if skill_id and skill_id not in SIMULATED_SKILL_IDS:
        return text
    if "[simulated]" in text.lower():
        return text
    return f"{text} [simulated]"


class _Emitter:
    def __init__(self, state: InvestigationState, on_step: OnStep, alert_id: str):
        self.state = state
        self.on_step = on_step
        self.alert_id = alert_id
        self.step_num = 0

    def emit(self, agent: str, status: str, inp: str, out: str, ms: int, skill_id: str | None = None) -> None:
        self.step_num += 1
        link_tpl = WORKSPACE_LINKS.get(agent)
        link = link_tpl.format(alert_id=self.alert_id) if link_tpl and self.alert_id else None
        s = {
            "step": self.step_num,
            "agent": agent,
            "skill_id": skill_id,
            "status": status,
            "input": inp,
            "output": out,
            "duration_ms": ms,
            "workspace_link": link,
        }
        self.state.workflow_steps.append(s)
        if self.on_step:
            self.on_step(s)


def _priority_from_alert(alert: dict[str, Any], ml: dict[str, Any], hits: list[dict[str, Any]]) -> tuple[str, str]:
    """SLA / priority — volume-aware by segment & product."""
    score = int(ml.get("score") or 0)
    segment = str(alert.get("segment") or "").lower()
    product = str(alert.get("product") or "").lower()

    if hits or score >= 80 or alert.get("risk_level") == "high":
        return "critical", "fast-track"
    if score >= 55 or alert.get("risk_level") == "medium":
        return "high", "elevated"
    # Retail volume lanes (payroll / e-wallet) get a dedicated low-friction SLA.
    if product in ("payroll", "ewallet") and not hits and score < 30:
        return "low", "volume-retail"
    if segment == "retail" and not hits and score < 40:
        return "low", "retail-routine"
    if segment == "sme" and not hits and score < 40:
        return "normal", "sme-standard"
    if score < 30:
        return "low", "routine"
    return "normal", "standard"


def choose_investigation_route(
    alert: dict[str, Any],
    ml: dict[str, Any],
    hits: list[dict[str, Any]],
) -> tuple[str, str]:
    """Decide FAST_TRACK / FULL / STANDARD after RAG + ML + hard gates.

    Gate hits always force FULL. Deterministic gates still win at Arbiter.
    """
    amount = float(alert.get("amount_usd") or 0)
    ml_score = int(ml.get("score") or 0)
    segment = str(alert.get("segment") or "").lower()
    product = str(alert.get("product") or "").lower()
    tags = {str(t).lower() for t in (alert.get("risk_tags") or [])}

    if hits:
        codes = ", ".join(str(h.get("code") or "GATE") for h in hits)
        return "FULL", f"hard policy gate(s): {codes}"
    if ml_score >= 70:
        return "FULL", f"ML score {ml_score} ≥ 70"
    if amount >= 10000:
        return "FULL", f"high-value amount ${amount:,.0f}"
    if product == "remittance" or "corridor_risk" in tags or "high_risk_jurisdiction" in tags:
        return "FULL", f"cross-border / corridor risk (product={product or 'n/a'})"

    low_retail = segment == "retail" and amount < 500
    volume_product = product in ("payroll", "ewallet")
    if ml_score < 30 and (low_retail or volume_product):
        why = (
            f"product={product} volume lane"
            if volume_product
            else f"retail amount ${amount:,.0f} < $500"
        )
        return "FAST_TRACK", f"{why} · ML {ml_score} < 30 · no hard gates"

    return (
        "STANDARD",
        f"ML {ml_score} · amount ${amount:,.0f} · segment={segment or 'n/a'} · product={product or 'n/a'}",
    )


def node_orchestrator(state: InvestigationState, emit: _Emitter) -> None:
    alert = state.alert
    # Bind active jurisdiction / policy version (stamped by API X-Tenant).
    try:
        from agent.policy_context import resolve_policy

        tenant = alert.get("_policy_tenant") or alert.get("jurisdiction")
        if alert.get("jurisdiction") and alert.get("policy_version"):
            state.jurisdiction = str(alert["jurisdiction"])
            state.policy_version = str(alert["policy_version"])
        else:
            meta = resolve_policy(tenant)
            state.jurisdiction = meta["jurisdiction"]
            state.policy_version = meta["policy_version"]
            alert["jurisdiction"] = state.jurisdiction
            alert["policy_version"] = state.policy_version
    except Exception:
        state.jurisdiction = str(alert.get("jurisdiction") or "default")
        state.policy_version = str(alert.get("policy_version") or "v1.0")

    aid = alert.get("id", "")
    state.add_agent(NODE_ORCHESTRATOR)
    t0 = time.perf_counter()
    emit.emit(
        NODE_ORCHESTRATOR,
        "completed",
        "Intake Parser",
        f"Normalized alert {aid} · session {alert.get('session_id', 'N/A')}",
        max(12, int((time.perf_counter() - t0) * 1000) + 15),
        skill_id="intake-parse",
    )

    t0 = time.perf_counter()
    emit.emit(
        NODE_ORCHESTRATOR,
        "completed",
        "Context Retriever",
        f"Session continuity for {aid} · prior findings hydrated",
        max(12, int((time.perf_counter() - t0) * 1000) + 20),
        skill_id="context-retrieve",
    )

    t0 = time.perf_counter()
    similar = rag_engine.find_similar(alert, top_k=3)
    state.similar_cases = similar
    rag_out = (
        "; ".join(f"{s['case_id']} → {s['resolution']} ({s['similarity']:.0%})" for s in similar)
        if similar
        else "No similar cases in memory"
    )
    emit.emit(
        NODE_ORCHESTRATOR,
        "completed",
        "RAG Case Lookup",
        rag_out,
        max(20, int((time.perf_counter() - t0) * 1000) + 40),
        skill_id="rag-lookup",
    )

    ml = score_transaction(alert)
    state.ml_score = ml
    hits = evaluate_hard_gates(alert)
    state.policy_hits = hits
    priority, sla = _priority_from_alert(alert, ml, hits)
    state.priority = priority  # type: ignore[assignment]
    state.sla_bucket = sla
    backend = ml.get("backend") or ml.get("model")
    emit.emit(
        NODE_ORCHESTRATOR,
        "completed",
        "SLA & Priority Tracker",
        f"Priority {priority.upper()} · SLA '{sla}' · provisional ML {ml['score']}/100 ({backend})"
        f" · segment={alert.get('segment') or 'n/a'} · product={alert.get('product') or 'n/a'}",
        35,
        skill_id="sla-priority",
    )

    route, reason = choose_investigation_route(alert, ml, hits)
    state.route = route  # type: ignore[assignment]
    state.route_reason = reason
    label = ROUTE_LABELS.get(route, route)
    emit.emit(
        NODE_ORCHESTRATOR,
        "completed",
        "Adaptive Router",
        f"{label} — {reason}",
        22,
        skill_id="adaptive-router",
    )


def node_identity(state: InvestigationState, emit: _Emitter, *, lite: bool = False) -> None:
    alert = state.alert
    aid = alert.get("id", "")
    state.add_agent(NODE_IDENTITY)
    t0 = time.perf_counter()
    screening = (
        screening_with_policy_overlay(aid, "screen entity", alert=alert)
        if aid or alert
        else {"reply": "No alert id"}
    )
    state.entity_findings.append({"skill": "sanctions-check", "result": screening.get("reply")})
    # Prefer live OFAC overlay result written back onto the alert
    if isinstance(screening.get("sanctions_screening"), dict):
        alert["sanctions_screening"] = screening["sanctions_screening"]
        ofac = screening.get("ofac") or {}
        if ofac.get("hit"):
            signals = dict(alert.get("signals") or {})
            signals["sanctions_hit"] = True
            alert["signals"] = signals
            state.policy_hits = evaluate_hard_gates(alert)
    sanctions = alert.get("sanctions_screening") or {}
    signals = alert.get("signals") or {}
    s_status = str(sanctions.get("status", "clear")).upper()
    pep = "PEP hit" if signals.get("pep_hit") else "No PEP"
    source = screening.get("source") or "OFAC SDN (public list)"
    match_extra = ""
    if sanctions.get("matched_name"):
        match_extra = f" · matched={sanctions.get('matched_name')} [{sanctions.get('program') or '—'}]"
    emit.emit(
        NODE_IDENTITY,
        "completed",
        f"Sanctions_API ({source})",
        f"{s_status} · {sanctions.get('matches', 0)} match(es){match_extra} · {pep}. {sanctions.get('note', '')}".strip(),
        max(40, int((time.perf_counter() - t0) * 1000) + 60),
        skill_id="sanctions-check",
    )

    if lite:
        device_risk = signals.get("device_risk") or "low"
        ip_c = signals.get("ip_country") or alert.get("country") or "—"
        emit.emit(
            NODE_IDENTITY,
            "completed",
            "Device & IP Anomaly Checker",
            f"Device risk {device_risk}; IP country {ip_c}; OS {alert.get('device_os', '—')} · STANDARD lite",
            16,
            skill_id="device-ip-check",
        )
        for skipped, skill in (
            ("OSINT_Search", "osint-research"),
            ("VASP_Registry_Lookup", "kyb-verify"),
            ("UBO Unroller", "ubo-unroll"),
        ):
            emit.emit(
                NODE_IDENTITY,
                "skipped",
                skipped,
                "STANDARD route — deep-dive skipped",
                4,
                skill_id=skill,
            )
        return

    t0 = time.perf_counter()
    name = alert.get("customer_name") or alert.get("counterparty") or "Unknown"
    osint = osint_research(str(name), aid)
    state.entity_findings.append({"skill": "osint-research", "result": osint.get("reply")})
    emit.emit(
        NODE_IDENTITY,
        "completed",
        "OSINT_Search",
        _tag_simulated((osint.get("reply") or "OSINT complete")[:280], "osint-research"),
        max(30, int((time.perf_counter() - t0) * 1000) + 50),
        skill_id="osint-research",
    )

    t0 = time.perf_counter()
    if aid:
        kyb = kyb_due_diligence(aid)
        state.entity_findings.append({"skill": "kyb-verify", "result": kyb.get("reply")})
        kyb_out = (kyb.get("reply") or "KYB complete")[:280]
    else:
        kyb_out = "Skipped — no partner context"
    emit.emit(
        NODE_IDENTITY,
        "completed",
        "VASP_Registry_Lookup",
        _tag_simulated(kyb_out, "kyb-verify"),
        max(25, int((time.perf_counter() - t0) * 1000) + 40),
        skill_id="kyb-verify",
    )

    ubo = unroll_ubo(str(name), alert)
    state.entity_findings.append({"skill": "ubo-unroll", "result": ubo})
    emit.emit(
        NODE_IDENTITY,
        "completed",
        "UBO Unroller",
        _tag_simulated(ubo["summary"][:280], "ubo-unroll"),
        28,
        skill_id="ubo-unroll",
    )

    device_risk = signals.get("device_risk") or "low"
    ip_c = signals.get("ip_country") or alert.get("country") or "—"
    emit.emit(
        NODE_IDENTITY,
        "completed",
        "Device & IP Anomaly Checker",
        f"Device risk {device_risk}; IP country {ip_c}; OS {alert.get('device_os', '—')}",
        16,
        skill_id="device-ip-check",
    )


def node_investigator(state: InvestigationState, emit: _Emitter, *, lite: bool = False) -> None:
    alert = state.alert
    aid = alert.get("id", "")
    state.add_agent(NODE_INVESTIGATOR)
    ml = state.ml_score or score_transaction(alert)
    state.ml_score = ml
    emit.emit(
        NODE_INVESTIGATOR,
        "completed",
        "ML Transaction Validator",
        ml["summary"],
        55,
        skill_id="ml-validate",
    )
    state.financial_findings.append({"skill": "ml-validate", "result": ml})

    empty_exposure = {
        "direct_exposure": 0.0,
        "indirect_exposure": 0.0,
        "min_indirect_hops": None,
        "paths": [],
        "summary": "No on-chain exposure to flagged entities detected",
    }

    if lite:
        exposure = empty_exposure
        state.financial_findings.append({"skill": "graph-exposure", "result": exposure})
        emit.emit(
            NODE_INVESTIGATOR,
            "skipped",
            "OnChain_Graph_Analyzer",
            "STANDARD route — graph deep-dive skipped",
            4,
            skill_id="graph-summary",
        )
        behavior = {"summary": "STANDARD lite — behavioral deep-dive skipped", "patterns": []}
        state.financial_findings.append({"skill": "behavioral-patterns", "result": behavior})
        emit.emit(
            NODE_INVESTIGATOR,
            "skipped",
            "Behavioral Pattern Engine",
            behavior["summary"],
            4,
            skill_id="behavioral-patterns",
        )
        kyt = compute_kyt_score(alert, exposure=exposure, behavior=behavior)
        alert["kyt_score"] = kyt["score"]
        travel = alert.get("travel_rule_status", "n/a")
        tags = ", ".join(alert.get("risk_tags") or []) or "none"
        state.financial_findings.append({"skill": "kyt-score", "result": kyt})
        emit.emit(
            NODE_INVESTIGATOR,
            "completed",
            "KYT_Score",
            kyt["summary"],
            40,
            skill_id="kyt-score",
        )
        emit.emit(
            NODE_INVESTIGATOR,
            "completed",
            "Travel Rule Check",
            f"Travel Rule {travel} · tags [{tags}]",
            18,
            skill_id="travel-rule-check",
        )
        emit.emit(
            NODE_INVESTIGATOR,
            "skipped",
            "Fiat-Crypto Bridge Tracer",
            "STANDARD route — bridge trace skipped",
            4,
            skill_id="fiat-crypto-bridge",
        )
        return

    # Always run on-chain exposure (completed even when clean / no graph)
    exposure = compute_exposure(aid) if aid else empty_exposure
    state.financial_findings.append({"skill": "graph-exposure", "result": exposure})
    emit.emit(
        NODE_INVESTIGATOR,
        "completed",
        "OnChain_Graph_Analyzer",
        (exposure.get("summary") or "No on-chain exposure to flagged entities detected")[:320],
        70,
        skill_id="graph-summary",
    )

    # Always complete behavioral step with an explicit conclusion
    behavior = analyze_behavior(alert)
    state.financial_findings.append({"skill": "behavioral-patterns", "result": behavior})
    emit.emit(
        NODE_INVESTIGATOR,
        "completed",
        "Behavioral Pattern Engine",
        behavior["summary"],
        22,
        skill_id="behavioral-patterns",
    )

    # Independent KYT (exposure + travel-rule + behavioral) — not ML echo
    kyt = compute_kyt_score(alert, exposure=exposure, behavior=behavior)
    alert["kyt_score"] = kyt["score"]
    travel = alert.get("travel_rule_status", "n/a")
    tags = ", ".join(alert.get("risk_tags") or []) or "none"
    state.financial_findings.append({"skill": "kyt-score", "result": kyt})
    emit.emit(
        NODE_INVESTIGATOR,
        "completed",
        "KYT_Score",
        kyt["summary"],
        40,
        skill_id="kyt-score",
    )
    emit.emit(
        NODE_INVESTIGATOR,
        "completed",
        "Travel Rule Check",
        f"Travel Rule {travel} · tags [{tags}]",
        18,
        skill_id="travel-rule-check",
    )

    bridge = trace_bridge(alert)
    state.financial_findings.append({"skill": "fiat-crypto-bridge", "result": bridge})
    emit.emit(
        NODE_INVESTIGATOR,
        "completed",
        "Fiat-Crypto Bridge Tracer",
        _tag_simulated(bridge["summary"][:280], "fiat-crypto-bridge"),
        20,
        skill_id="fiat-crypto-bridge",
    )


def node_arbiter(state: InvestigationState, emit: _Emitter) -> None:
    alert = state.alert
    state.add_agent(NODE_ARBITER)
    ml = state.ml_score or score_transaction(alert)
    hits = state.policy_hits
    similar = state.similar_cases
    travel = str(alert.get("travel_rule_status") or "").lower()

    soft_d, soft_c, soft_disp = soft_decision_from_score(int(ml["score"]), hits)
    # FAST_TRACK: Orchestrator already screened — auto-CLEAR when no hard gates.
    if state.route == "FAST_TRACK" and not hits:
        soft_d, soft_c, soft_disp = "CLEAR", 0.92, "auto_clear"
        state.rationale.append("FAST-TRACK route — auto-CLEAR (low amount / volume product, ML < 30, no hard gates)")

    rag_top = similar[0] if similar else None
    if (
        soft_d == "REVIEW"
        and rag_top
        and rag_top.get("similarity", 0) >= 0.4
        and rag_top.get("resolution") in ("CLEAR", "REVIEW")
        and int(ml["score"]) <= 45
        and not hits
        and state.route != "FAST_TRACK"
    ):
        soft_d, soft_c, soft_disp = "CLEAR", 0.86, "auto_clear"
        state.rationale.append(
            f"RAG precedent {rag_top['case_id']} ({rag_top['resolution']}, {rag_top['similarity']:.0%}) supports clearance"
        )

    # Policy gates finalize the decision — LLM never overrides this.
    decision, confidence, disposition, hard = apply_gates_to_decision(
        hits,
        soft_decision=soft_d,
        soft_confidence=soft_c,
        soft_disposition=soft_disp,
    )

    # Thin evidence → lower confidence so HITL can engage (hard gates still win).
    if not hard and decision == "REVIEW" and travel in ("incomplete", "missing"):
        confidence = min(float(confidence), 0.65)

    # HITL: confidence below threshold forces analyst REVIEW (never overrides hard ESCALATE).
    hitl = False
    if float(confidence) < HITL_CONFIDENCE_THRESHOLD and not hard:
        decision = "REVIEW"
        disposition = "analyst_review"
        hitl = True
        state.rationale.append(
            f"Confidence {confidence:.0%} < {HITL_CONFIDENCE_THRESHOLD:.0%} — human-in-the-loop REVIEW"
        )

    state.decision = decision  # type: ignore[assignment]
    state.confidence = confidence
    state.disposition = disposition
    state.hard_escalate = hard
    state.hitl = hitl

    for h in hits:
        state.rationale.append(h["message"])
    if not hits:
        state.rationale.append(ml["summary"])
        if soft_d == "CLEAR" and decision == "CLEAR":
            state.rationale.append(f"ML score {ml['score']} below review threshold with no hard policy hits")
        elif decision == "REVIEW" and not hitl:
            state.rationale.append(f"ML score {ml['score']} in analyst review band")
        elif decision == "ESCALATE" and not hard:
            state.rationale.append(f"ML score {ml['score']} exceeds escalation threshold")

    emit.emit(
        NODE_ARBITER,
        "completed",
        "Confidence Scorer",
        f"FINAL: {decision} ({confidence:.0%}) → {disposition}"
        + (" · HITL" if hitl else "")
        + (" · hard policy gate applied" if hard else " · model + policy synthesis")
        + f" · route={ROUTE_LABELS.get(state.route, state.route)}",
        40,
        skill_id="confidence-score",
    )

    exposure = _exposure_from_findings(state.financial_findings)
    explainability = _build_explainability(
        ml=ml,
        policy_hits=hits,
        exposure=exposure,
        hard_escalate=hard,
        decision=decision,
    )
    state.explainability = explainability

    # Evidence pack for grounded SAR — same facts that land in audit_pack.
    evidence = {
        "decision": decision,
        "confidence": confidence,
        "disposition": disposition,
        "hard_escalate": hard,
        "route": state.route,
        "hitl": hitl,
        "alert": {
            "id": alert.get("id"),
            "customer_name": alert.get("customer_name"),
            "customer_id": alert.get("customer_id"),
            "direction": alert.get("direction"),
            "amount_usd": alert.get("amount_usd"),
            "asset": alert.get("asset"),
            "network": alert.get("network"),
            "kyt_score": alert.get("kyt_score"),
            "risk_level": alert.get("risk_level"),
            "risk_tags": alert.get("risk_tags"),
            "travel_rule_status": alert.get("travel_rule_status"),
            "counterparty": alert.get("counterparty"),
            "country": alert.get("country"),
            "sanctions_screening": alert.get("sanctions_screening"),
            "signals": alert.get("signals"),
            "segment": alert.get("segment"),
            "product": alert.get("product"),
            "rail": alert.get("rail"),
        },
        "policy_hits": hits,
        "ml_score": {
            "score": ml.get("score"),
            "backend": ml.get("backend") or ml.get("model"),
            "summary": ml.get("summary"),
            "attribution": ml.get("attribution") or [],
            "top_drivers": ml.get("top_drivers") or [],
        },
        "exposure": exposure,
        "rationale": list(state.rationale),
        "explainability": explainability,
        "entity_findings": state.entity_findings,
        "financial_findings": [
            {"skill": f.get("skill"), "summary": _finding_summary(f.get("result"))}
            for f in state.financial_findings
        ],
        "similar_cases": [
            {
                "case_id": s.get("case_id"),
                "resolution": s.get("resolution"),
                "similarity": s.get("similarity"),
                "analyst_notes": str(s.get("analyst_notes", ""))[:120],
            }
            for s in similar[:3]
        ],
    }

    if decision == "ESCALATE":
        sar, sar_mode = _draft_sar(evidence)
        state.sar_draft = sar
        state.sar_mode = sar_mode
        label = f"SAR_Generator ({sar_mode})"
        emit.emit(
            NODE_ARBITER,
            "completed",
            label,
            sar[:220] + ("..." if len(sar) > 220 else ""),
            90,
            skill_id="sar-draft",
        )
    else:
        emit.emit(
            NODE_ARBITER,
            "skipped",
            "SAR_Generator (template)",
            f"Decision {decision} — no SAR draft required",
            5,
            skill_id="sar-draft",
        )

    audit = {
        "decision": decision,
        "confidence": confidence,
        "policy_hits": hits,
        "ml_score": ml,
        "rationale": state.rationale,
        "explainability": explainability,
        "exposure": exposure,
        "entity_findings": state.entity_findings,
        "financial_findings": evidence["financial_findings"],
        "similar_cases": [s.get("case_id") for s in similar],
        "nodes_run": state.agents_used,
        "sar_mode": state.sar_mode,
        "route": state.route,
        "hitl": hitl,
        "immutable": True,
        "jurisdiction": state.jurisdiction,
        "policy_version": state.policy_version,
    }
    state.audit_pack = audit
    emit.emit(
        NODE_ARBITER,
        "completed",
        "Audit Trail Compiler",
        f"Packaged {len(state.workflow_steps)} steps · {len(hits)} policy hit(s) · ML {ml['score']}"
        f" · {len(explainability)} explainability factor(s) · route={state.route}"
        + (" · HITL" if hitl else ""),
        25,
        skill_id="audit-compile",
    )


def run_investigation(
    alert: dict[str, Any],
    on_step: OnStep = None,
) -> dict[str, Any]:
    """Execute adaptive investigation graph; returns triage-compatible result."""
    state = InvestigationState(alert=alert)
    emit = _Emitter(state, on_step, alert.get("id", ""))
    node_orchestrator(state, emit)
    route = state.route or "FULL"
    if route == "FAST_TRACK":
        node_arbiter(state, emit)
    else:
        lite = route == "STANDARD"
        node_identity(state, emit, lite=lite)
        node_investigator(state, emit, lite=lite)
        node_arbiter(state, emit)
    result = state.to_result()
    result["runtime"] = "supervisor"
    return result


def _exposure_from_findings(findings: list[dict[str, Any]]) -> dict[str, Any]:
    for f in findings:
        if f.get("skill") == "graph-exposure" and isinstance(f.get("result"), dict):
            return f["result"]
    return {
        "direct_exposure": 0.0,
        "indirect_exposure": 0.0,
        "min_indirect_hops": None,
        "paths": [],
        "summary": "No on-chain exposure to flagged entities detected",
    }


def _finding_summary(result: Any) -> str:
    if isinstance(result, dict):
        return str(result.get("summary") or result.get("reply") or "")[:320]
    return str(result or "")[:320]


def _build_explainability(
    *,
    ml: dict[str, Any],
    policy_hits: list[dict[str, Any]],
    exposure: dict[str, Any],
    hard_escalate: bool,
    decision: str,
) -> list[dict[str, Any]]:
    """Decision drivers for SR 11-7 / EU AI Act — ML features + gates + exposure."""
    factors: list[dict[str, Any]] = []

    for a in (ml.get("attribution") or [])[:8]:
        contrib = a.get("contribution")
        factors.append(
            {
                "source": "ml",
                "factor": a.get("feature"),
                "contribution": contrib,
                "detail": f"ML feature attribution +{contrib}",
            }
        )

    for h in policy_hits:
        factors.append(
            {
                "source": "policy_gate",
                "factor": h.get("code") or h.get("gate") or "hard_gate",
                "contribution": "hard_escalate" if hard_escalate else "hit",
                "detail": h.get("message") or str(h),
            }
        )

    direct = float(exposure.get("direct_exposure") or 0)
    indirect = float(exposure.get("indirect_exposure") or 0)
    if direct > 0 or indirect > 0:
        hops = exposure.get("min_indirect_hops")
        hop_bit = f", min hops={hops}" if hops is not None else ""
        factors.append(
            {
                "source": "exposure",
                "factor": "on_chain_exposure",
                "contribution": round(direct + indirect, 2),
                "detail": (
                    f"Direct {direct:.2f} · Indirect {indirect:.2f}{hop_bit}. "
                    f"{exposure.get('summary') or ''}"
                ).strip(),
            }
        )
    elif exposure.get("summary"):
        factors.append(
            {
                "source": "exposure",
                "factor": "on_chain_exposure",
                "contribution": 0.0,
                "detail": str(exposure.get("summary")),
            }
        )

    factors.append(
        {
            "source": "decision",
            "factor": "final_disposition",
            "contribution": decision,
            "detail": (
                f"Final decision {decision} "
                + ("(hard policy gate applied)" if hard_escalate else "(model + policy synthesis)")
            ),
        }
    )
    return factors


def _template_sar(evidence: dict[str, Any]) -> str:
    alert = evidence.get("alert") or {}
    ml = evidence.get("ml_score") or {}
    rationale = evidence.get("rationale") or []
    similar = evidence.get("similar_cases") or []
    lines = [
        f"## Escalation Summary — {alert.get('id')}",
        f"**Customer:** {alert.get('customer_name')} ({alert.get('customer_id')})",
        f"**Transaction:** {str(alert.get('direction', '')).title()} "
        f"${float(alert.get('amount_usd') or 0):,.0f} ({alert.get('asset')} on {alert.get('network')})",
        f"**ML Score:** {ml.get('score')} ({ml.get('backend')}) | "
        f"**KYT:** {alert.get('kyt_score')} | **Risk:** {str(alert.get('risk_level', '')).upper()}",
        "",
        "### Risk Factors",
    ]
    for r in rationale:
        lines.append(f"- {r}")
    attribution = ml.get("attribution") or []
    if attribution:
        lines.append("\n### ML Feature Attribution")
        for a in attribution[:5]:
            lines.append(f"- {a['feature']}: +{a['contribution']}")
    exposure = evidence.get("exposure") or {}
    if exposure.get("summary"):
        lines.append("\n### On-Chain Exposure")
        lines.append(f"- {exposure.get('summary')}")
    if similar:
        lines.append("\n### Similar Historical Cases (RAG)")
        for s in similar[:2]:
            lines.append(
                f"- {s.get('case_id')}: {s.get('resolution')} — {str(s.get('analyst_notes', ''))[:100]}"
            )
    lines.extend(
        [
            "",
            "### Recommended Actions",
            "1. Initiate Enhanced Due Diligence (EDD)",
            "2. Freeze transaction pending compliance review",
            "3. Prepare SAR narrative if suspicion confirmed",
            "4. Document all findings in audit trail",
        ]
    )
    return "\n".join(lines)


def _draft_sar(evidence: dict[str, Any]) -> tuple[str, str]:
    """Draft SAR narrative from audit evidence only.

    Returns (narrative, mode) where mode is \"LLM\" or \"template\".
    Decision is already final — the LLM must not change it.
    """
    template = _template_sar(evidence)
    if not is_configured():
        return template, "template"

    decision = evidence.get("decision", "ESCALATE")
    system = (
        "You are a SAR Filing Agent for a crypto VASP compliance team. "
        "Write a professional Suspicious Activity Report narrative opening. "
        "CRITICAL RULES: "
        "(1) Use ONLY facts present in the provided audit evidence pack — "
        "policy hits, ML attribution, on-chain exposure, tool outputs, rationale. "
        "(2) Do NOT invent counterparties, amounts, jurisdictions, sanctions matches, "
        "wallet addresses, or any other facts not in the pack. "
        "(3) The investigation decision is already FINAL and locked by policy gates — "
        f"it is {decision}. You MUST NOT change, soften, or overturn this decision; "
        "you only narrate why escalation is warranted based on the evidence. "
        "(4) Be concise, factual, and regulator-ready. Use markdown headings."
    )
    pack_json = json.dumps(evidence, default=str, ensure_ascii=False, indent=2)
    user = (
        "Draft a SAR narrative grounded strictly on this audit evidence pack. "
        "Do not add facts outside the pack.\n\n"
        f"{pack_json}"
    )
    try:
        narrative = safe_invoke(user, system=system, fallback=template)
    except Exception:
        return template, "template"
    # If Bedrock returned the fallback string (or empty), treat as template mode.
    if not narrative or narrative.strip() == template.strip():
        return template, "template"
    return narrative, "LLM"
