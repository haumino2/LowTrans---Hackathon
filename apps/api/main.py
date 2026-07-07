from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from agent.analyst import analyze_question, generate_sql, run_analyst_query
from agent.bedrock import health_check as bedrock_health
from agent.bedrock import invoke_claude, is_configured
from agent.copilot import handle_copilot
from agent.rag import rag_engine
from agent.skills.registry import list_agents, list_skills
from agent.triage import stream_triage_events, triage_alert, triage_all_pending, write_override_audit
from db.models import init_db, is_db_ready
from db.repository import (
    DATA_DIR,
    append_audit,
    export_audit_csv,
    get_alert,
    run_sql_query,
    load_alerts,
    load_audit,
    load_copilot_sessions,
    load_resolved_cases,
    reset_demo,
    save_alerts,
)

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if init_db():
        from db.models import TransactionRow, get_session

        session = get_session()
        try:
            if session.query(TransactionRow).count() == 0:
                from scripts.seed_db import seed

                seed()
        finally:
            session.close()
    yield


app = FastAPI(
    title="LowTrans API",
    description="Agent Platform for AML and KYT for Crypto — RAG-powered triage",
    version="2.0.0",
    lifespan=lifespan,
)

API_KEY = os.getenv("LOWTRANS_API_KEY")  # if set, requires X-API-Key
TENANT_DEFAULT = os.getenv("LOWTRANS_TENANT", "demo")

# In-memory metrics for pilot readiness (non-prod)
METRICS: dict[str, Any] = {
    "requests_total": 0,
    "requests_by_path": {},
    "errors_total": 0,
    "latency_ms_sum": 0.0,
}

@app.middleware("http")
async def auth_and_metrics(request: Request, call_next):
    start = time.perf_counter()
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())

    # Auth (Phase J): if LOWTRANS_API_KEY set, require X-API-Key on /api/* (except health/docs)
    if API_KEY and request.url.path.startswith("/api/"):
        if request.url.path in ("/api/health", "/api/auth/roles"):
            pass
        else:
            if request.headers.get("X-API-Key") != API_KEY:
                return PlainTextResponse("Unauthorized", status_code=401, headers={"X-Request-Id": request_id})

    try:
        response = await call_next(request)
    except Exception:
        METRICS["errors_total"] += 1
        raise
    finally:
        dur_ms = (time.perf_counter() - start) * 1000
        METRICS["requests_total"] += 1
        METRICS["latency_ms_sum"] += dur_ms
        p = request.url.path
        METRICS["requests_by_path"][p] = METRICS["requests_by_path"].get(p, 0) + 1
    response.headers["X-Request-Id"] = request_id
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CopilotRequest(BaseModel):
    message: str
    alert_id: str | None = None
    session_id: str | None = None


class OverrideRequest(BaseModel):
    decision: str
    reason: str


class AssignRequest(BaseModel):
    assignee: str


class NoteRequest(BaseModel):
    note: str


class CaseStateRequest(BaseModel):
    state: str
    reason: str | None = None


class RuleCompileRequest(BaseModel):
    """Very small 'rule builder' request for demo/pilot."""

    name: str
    description: str | None = None
    # Supported primitives: mixer_exposure, sanctions_hit, kyt_min, amount_min, travel_rule_status, direction
    conditions: dict[str, Any]


ROLES = {"analyst", "supervisor", "auditor"}


def _role(x_role: str | None) -> str:
    if x_role and x_role.lower() in ROLES:
        return x_role.lower()
    return "analyst"


def _tenant(x_tenant: str | None) -> str:
    if x_tenant:
        return x_tenant.strip().lower()
    return TENANT_DEFAULT


class AnalystPreviewRequest(BaseModel):
    question: str


class AnalystRunRequest(BaseModel):
    sql: str


class BedrockChatRequest(BaseModel):
    message: str
    system: str = "You are a helpful AML compliance assistant for LowTrans."


@app.get("/")
def root():
    return {"service": "LowTrans", "tagline": "Agent Platform for AML & KYT for Crypto"}


@app.get("/api/health")
def health(bedrock_live: bool = False):
    from db.models import is_sqlite

    return {
        "status": "ok",
        "rag_cases_loaded": len(rag_engine.cases),
        "rag_backend": rag_engine.backend,
        "db_connected": is_db_ready(),
        "db_backend": "sqlite" if is_sqlite() else ("postgres" if is_db_ready() else "json"),
        "bedrock": bedrock_health(live=bedrock_live),
        "agents_registered": len(list_agents()),
        "skills_registered": len(list_skills()),
        "pipeline_steps": 11,
        "platform": "Agent → Skills → Tools",
        "tenant_default": TENANT_DEFAULT,
    }


@app.get("/api/metrics")
def metrics():
    avg = 0.0
    if METRICS["requests_total"]:
        avg = METRICS["latency_ms_sum"] / METRICS["requests_total"]
    return {**METRICS, "latency_ms_avg": round(avg, 2)}


# --- Phase: Rule Builder (pilot-grade, not production DSL) ---
RULES_MEM: list[dict[str, Any]] = []


def _rule_to_sql(conditions: dict[str, Any]) -> str:
    clauses: list[str] = []
    if conditions.get("mixer_exposure") is True:
        clauses.append("mixer_exposure = 1")
    if conditions.get("sanctions_hit") is True:
        clauses.append("sanctions_hit = 1")
    if isinstance(conditions.get("kyt_min"), (int, float)):
        clauses.append(f"kyt_score >= {int(conditions['kyt_min'])}")
    if isinstance(conditions.get("amount_min"), (int, float)):
        clauses.append(f"amount_usd >= {float(conditions['amount_min'])}")
    if isinstance(conditions.get("direction"), str) and conditions["direction"].strip():
        direction = conditions["direction"].strip().lower()
        if direction in ("deposit", "withdrawal"):
            clauses.append(f"direction = '{direction}'")
    if isinstance(conditions.get("travel_rule_status"), str) and conditions["travel_rule_status"].strip():
        tr = conditions["travel_rule_status"].strip().lower()
        clauses.append(f"travel_rule_status = '{tr}'")
    where = " AND ".join(clauses) if clauses else "1=1"
    return (
        "SELECT COUNT(*) AS matches, "
        "ROUND(AVG(kyt_score), 2) AS avg_kyt, "
        "ROUND(AVG(amount_usd), 2) AS avg_amount "
        f"FROM transactions WHERE {where}"
    )


@app.post("/api/rules/compile")
def compile_rule(body: RuleCompileRequest, x_role: str | None = Header(default=None)):
    role = _role(x_role)
    if role not in ("analyst", "supervisor"):
        raise HTTPException(403, "Not allowed")
    sql = _rule_to_sql(body.conditions or {})
    try:
        columns, rows = run_sql_query(sql)
        row = dict(zip(columns, rows[0])) if rows else {"matches": 0, "avg_kyt": None, "avg_amount": None}
    except Exception as e:
        row = {"error": str(e)}
    compiled = {
        "id": f"rule-{uuid.uuid4().hex[:8]}",
        "name": body.name.strip(),
        "description": body.description or "",
        "conditions": body.conditions,
        "sql": sql,
        "preview": row,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    RULES_MEM.append(compiled)
    append_audit(
        {
            "timestamp": compiled["created_at"],
            "event_type": "rule_compile",
            "alert_id": "",
            "customer_id": "",
            "customer_name": "",
            "decision": "rule_compile",
            "reason": body.name,
            "role": role,
        }
    )
    return compiled


@app.get("/api/rules")
def list_rules():
    return list(reversed(RULES_MEM[-50:]))


@app.get("/api/auth/roles")
def auth_roles():
    return {
        "roles": [
            {"id": "analyst", "label": "Analyst", "permissions": ["triage", "override", "copilot"]},
            {"id": "supervisor", "label": "Supervisor", "permissions": ["triage", "override", "approve_escalate"]},
            {"id": "auditor", "label": "Auditor", "permissions": ["audit_read", "export"]},
        ],
        "demo_note": "Send X-Role header (analyst|supervisor|auditor) — mock RBAC for hackathon",
    }


@app.post("/api/bedrock/chat")
def bedrock_chat(body: BedrockChatRequest):
    if not is_configured():
        raise HTTPException(503, "Bedrock not configured.")
    try:
        reply = invoke_claude(body.message, system=body.system, max_tokens=512)
        return {"reply": reply, "model": bedrock_health()["model_id"]}
    except Exception as e:
        raise HTTPException(502, f"Bedrock error: {e}") from e


@app.get("/api/skills")
def skills():
    return {"agents": list_agents(), "skills": list_skills()}


@app.post("/api/copilot/chat")
def copilot_chat(body: CopilotRequest, x_role: str | None = Header(default=None)):
    _role(x_role)
    return handle_copilot(body.message, alert_id=body.alert_id, session_id=body.session_id)


@app.post("/api/copilot/chat/stream")
def copilot_chat_stream(body: CopilotRequest, x_role: str | None = Header(default=None)):
    """Stream copilot reply as SSE (token chunks)."""
    _role(x_role)

    def event_gen():
        try:
            result = handle_copilot(body.message, alert_id=body.alert_id, session_id=body.session_id)
            # Stream the already-generated reply in chunks (works even without Bedrock streaming).
            reply = str(result.get("reply", ""))
            meta = {k: v for k, v in result.items() if k != "reply"}
            yield f"data: {json.dumps({'event': 'meta', 'meta': meta})}\n\n"

            chunk = []
            for part in reply.split(" "):
                chunk.append(part)
                if len(chunk) >= 12:
                    yield f"data: {json.dumps({'event': 'token', 'text': ' '.join(chunk) + ' '})}\n\n"
                    chunk = []
            if chunk:
                yield f"data: {json.dumps({'event': 'token', 'text': ' '.join(chunk)})}\n\n"
            yield f"data: {json.dumps({'event': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/copilot/sessions/{session_id}")
def copilot_session(session_id: str):
    return {"session_id": session_id, "turns": load_copilot_sessions(session_id)}


@app.post("/api/analyst/preview")
def analyst_preview(body: AnalystPreviewRequest):
    return generate_sql(body.question)


@app.post("/api/analyst/ask")
def analyst_ask(body: AnalystPreviewRequest):
    """NL question → auto-run → visualization (no SQL step on UI)."""
    result = analyze_question(body.question)
    if result.get("blocked"):
        raise HTTPException(400, result.get("error", "Query blocked"))
    if result.get("error") and not result.get("visualization"):
        raise HTTPException(500, result["error"])
    return result


@app.post("/api/analyst/run")
def analyst_run(body: AnalystRunRequest):
    try:
        return run_analyst_query(body.sql)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@app.get("/api/alerts")
def list_alerts():
    return load_alerts()


def _case_id_from_alert(a: dict[str, Any]) -> str:
    # Phase K: case-centric grouping (default: customer_id)
    return str(a.get("case_id") or a.get("customer_id") or a.get("id"))


def _case_rollup(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    # status precedence: escalate_pending > escalate > review > clear > pending
    statuses = {str(a.get("status", "pending")) for a in alerts}
    if "escalate_pending" in statuses:
        status = "escalate_pending"
    elif "escalate" in statuses:
        status = "escalate"
    elif "review" in statuses:
        status = "review"
    elif "clear" in statuses:
        status = "clear"
    else:
        status = "pending"

    max_kyt = max(int(a.get("kyt_score", 0) or 0) for a in alerts)
    risk_levels = [str(a.get("risk_level", "low")) for a in alerts]
    risk = "high" if "high" in risk_levels else ("medium" if "medium" in risk_levels else "low")
    latest = max(str(a.get("created_at", "")) for a in alerts)

    head = alerts[0]
    case_id = _case_id_from_alert(head)
    return {
        "case_id": case_id,
        "customer_id": head.get("customer_id"),
        "customer_name": head.get("customer_name"),
        "partner": head.get("partner"),
        "country": head.get("country"),
        "risk_level": risk,
        "max_kyt": max_kyt,
        "status": status,
        "latest_alert_at": latest,
        "alerts_count": len(alerts),
        "assigned_to": head.get("case_assigned_to") or head.get("assigned_to"),
        "state": head.get("case_state") or "new",
    }


@app.get("/api/cases")
def list_cases():
    """Phase K: group alerts into cases (default customer_id)."""
    alerts = load_alerts()
    groups: dict[str, list[dict[str, Any]]] = {}
    for a in alerts:
        cid = _case_id_from_alert(a)
        groups.setdefault(cid, []).append(a)
    cases = [_case_rollup(v) for v in groups.values()]
    # default sort: high KYT first
    cases.sort(key=lambda c: int(c.get("max_kyt", 0)), reverse=True)
    return cases


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    alerts = load_alerts()
    matched = [a for a in alerts if _case_id_from_alert(a) == case_id]
    if not matched:
        raise HTTPException(404, "Case not found")
    matched.sort(key=lambda a: str(a.get("created_at", "")), reverse=True)
    head = matched[0]
    return {
        **_case_rollup(matched),
        "alerts": matched,
        "case_notes": head.get("case_notes") or [],
        "policy_version": (head.get("triage_result") or {}).get("policy_version"),
    }


@app.post("/api/cases/{case_id}/state")
def set_case_state(case_id: str, body: CaseStateRequest, x_role: str | None = Header(default=None)):
    role = _role(x_role)
    if role not in ("analyst", "supervisor"):
        raise HTTPException(403, "Not allowed")
    alerts = load_alerts()
    changed = 0
    for i, a in enumerate(alerts):
        if _case_id_from_alert(a) == case_id:
            alerts[i]["case_state"] = body.state.strip().lower()
            changed += 1
    if not changed:
        raise HTTPException(404, "Case not found")
    save_alerts(alerts)
    append_audit(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "case_state",
            "alert_id": "",
            "customer_id": case_id,
            "customer_name": "",
            "decision": body.state.strip().lower(),
            "reason": body.reason or "",
            "role": role,
        }
    )
    return {"ok": True, "case_id": case_id, "alerts_updated": changed, "state": body.state.strip().lower()}


@app.post("/api/cases/{case_id}/assign")
def assign_case(case_id: str, body: AssignRequest, x_role: str | None = Header(default=None)):
    role = _role(x_role)
    if role not in ("analyst", "supervisor"):
        raise HTTPException(403, "Not allowed")
    alerts = load_alerts()
    changed = 0
    for i, a in enumerate(alerts):
        if _case_id_from_alert(a) == case_id:
            alerts[i]["case_assigned_to"] = body.assignee.strip()
            changed += 1
    if not changed:
        raise HTTPException(404, "Case not found")
    save_alerts(alerts)
    append_audit(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "case_assign",
            "alert_id": "",
            "customer_id": case_id,
            "customer_name": "",
            "decision": "",
            "reason": f"Assigned to {body.assignee.strip()}",
            "role": role,
        }
    )
    return {"ok": True, "case_id": case_id, "assigned_to": body.assignee.strip()}


@app.post("/api/cases/{case_id}/notes")
def add_case_note(case_id: str, body: NoteRequest, x_role: str | None = Header(default=None)):
    role = _role(x_role)
    if role not in ("analyst", "supervisor"):
        raise HTTPException(403, "Not allowed")
    alerts = load_alerts()
    idxs = [i for i, a in enumerate(alerts) if _case_id_from_alert(a) == case_id]
    if not idxs:
        raise HTTPException(404, "Case not found")
    # store notes on the most recent alert in the case for simplicity
    newest_idx = max(idxs, key=lambda i: str(alerts[i].get("created_at", "")))
    notes = alerts[newest_idx].get("case_notes") or []
    if not isinstance(notes, list):
        notes = []
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "text": body.note.strip(),
    }
    notes.append(entry)
    alerts[newest_idx]["case_notes"] = notes[-50:]
    save_alerts(alerts)
    append_audit(
        {
            "timestamp": entry["timestamp"],
            "event_type": "case_note",
            "alert_id": "",
            "customer_id": case_id,
            "customer_name": "",
            "decision": "",
            "reason": body.note.strip()[:200],
            "role": role,
        }
    )
    return {"ok": True, "case_id": case_id, "notes": alerts[newest_idx]["case_notes"]}


@app.get("/api/approvals")
def approvals_inbox(x_role: str | None = Header(default=None)):
    role = _role(x_role)
    if role != "supervisor":
        raise HTTPException(403, "Supervisor role required")
    alerts = load_alerts()
    return [a for a in alerts if a.get("status") == "escalate_pending"]


@app.get("/api/alerts/{alert_id}")
def get_alert_endpoint(alert_id: str):
    alert = get_alert(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    return alert


@app.post("/api/alerts/{alert_id}/triage")
def triage(alert_id: str, x_role: str | None = Header(default=None)):
    _role(x_role)
    alerts = load_alerts()
    for i, a in enumerate(alerts):
        if a["id"] == alert_id:
            result = triage_alert(a)
            decision = result["decision"].lower()
            alerts[i]["status"] = "escalate_pending" if decision == "escalate" else decision
            alerts[i]["triage_result"] = result
            save_alerts(alerts)
            return result
    raise HTTPException(404, "Alert not found")


@app.get("/api/alerts/{alert_id}/triage/stream")
def triage_stream(alert_id: str):
    alert = get_alert(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")

    def event_gen():
        final_result = None
        for item in stream_triage_events(alert):
            if item.get("event") == "complete":
                final_result = item.get("result")
            yield f"data: {json.dumps(item)}\n\n"
        if final_result:
            alerts = load_alerts()
            for i, a in enumerate(alerts):
                if a["id"] == alert_id:
                    decision = final_result["decision"].lower()
                    alerts[i]["status"] = "escalate_pending" if decision == "escalate" else decision
                    alerts[i]["triage_result"] = final_result
                    save_alerts(alerts)
                    break

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/alerts/triage-all")
def triage_all():
    alerts = load_alerts()
    results = triage_all_pending(alerts)
    for result in results:
        for i, a in enumerate(alerts):
            if a["id"] == result["alert_id"]:
                alerts[i]["status"] = result["decision"].lower()
                alerts[i]["triage_result"] = result
    save_alerts(alerts)
    cleared = sum(1 for r in results if r["decision"] == "CLEAR")
    return {
        "total": len(results),
        "cleared": cleared,
        "auto_clear_rate": round(cleared / len(results) * 100, 1) if results else 0,
        "results": results,
    }


@app.get("/api/alerts/{alert_id}/similar")
def similar_cases(alert_id: str):
    alert = get_alert(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    return rag_engine.find_similar(alert, top_k=5)


@app.get("/api/alerts/{alert_id}/workflow")
def get_workflow(alert_id: str):
    alert = get_alert(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    triage = alert.get("triage_result")
    if not triage or not triage.get("workflow_steps"):
        raise HTTPException(404, "No workflow found — run triage first")
    return {
        "alert_id": alert_id,
        "workflow_steps": triage["workflow_steps"],
        "workflow_summary": triage.get("workflow_summary"),
        "decision": triage.get("decision"),
        "triaged_at": triage.get("triaged_at"),
    }


@app.post("/api/alerts/{alert_id}/override")
def override(alert_id: str, body: OverrideRequest, x_role: str | None = Header(default=None)):
    role = _role(x_role)
    if role == "auditor":
        raise HTTPException(403, "Auditor role cannot override decisions")
    if role != "supervisor" and body.decision.upper() == "ESCALATE":
        raise HTTPException(403, "Only supervisor can set ESCALATE")
    alerts = load_alerts()
    for i, a in enumerate(alerts):
        if a["id"] == alert_id:
            alerts[i]["status"] = body.decision.lower()
            alerts[i]["override"] = {
                "decision": body.decision,
                "reason": body.reason,
                "role": role,
            }
            save_alerts(alerts)
            write_override_audit(a, body.decision, body.reason, role=role)
            return {"ok": True, "alert_id": alert_id, "role": role}
    raise HTTPException(404, "Alert not found")


@app.post("/api/alerts/{alert_id}/assign")
def assign_alert(alert_id: str, body: AssignRequest, x_role: str | None = Header(default=None)):
    role = _role(x_role)
    if role not in ("analyst", "supervisor"):
        raise HTTPException(403, "Not allowed")
    alerts = load_alerts()
    for i, a in enumerate(alerts):
        if a["id"] == alert_id:
            alerts[i]["assigned_to"] = body.assignee.strip()
            save_alerts(alerts)
            append_audit(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event_type": "assign",
                    "alert_id": alert_id,
                    "customer_id": a.get("customer_id"),
                    "customer_name": a.get("customer_name"),
                    "decision": a.get("status", ""),
                    "reason": f"Assigned to {body.assignee.strip()}",
                    "role": role,
                }
            )
            return {"ok": True, "alert_id": alert_id, "assigned_to": alerts[i]["assigned_to"]}
    raise HTTPException(404, "Alert not found")


@app.post("/api/alerts/{alert_id}/notes")
def add_note(alert_id: str, body: NoteRequest, x_role: str | None = Header(default=None)):
    role = _role(x_role)
    if role not in ("analyst", "supervisor"):
        raise HTTPException(403, "Not allowed")
    alerts = load_alerts()
    for i, a in enumerate(alerts):
        if a["id"] == alert_id:
            notes = a.get("notes") or []
            if not isinstance(notes, list):
                notes = []
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "role": role,
                "text": body.note.strip(),
            }
            notes.append(entry)
            alerts[i]["notes"] = notes[-50:]
            save_alerts(alerts)
            append_audit(
                {
                    "timestamp": entry["timestamp"],
                    "event_type": "note",
                    "alert_id": alert_id,
                    "customer_id": a.get("customer_id"),
                    "customer_name": a.get("customer_name"),
                    "decision": a.get("status", ""),
                    "reason": body.note.strip()[:200],
                    "role": role,
                }
            )
            return {"ok": True, "alert_id": alert_id, "notes": alerts[i]["notes"]}
    raise HTTPException(404, "Alert not found")


@app.post("/api/alerts/{alert_id}/approve-escalation")
def approve_escalation(alert_id: str, x_role: str | None = Header(default=None)):
    role = _role(x_role)
    if role != "supervisor":
        raise HTTPException(403, "Supervisor role required")
    alerts = load_alerts()
    for i, a in enumerate(alerts):
        if a["id"] == alert_id:
            triage_result = a.get("triage_result") or {}
            if str(triage_result.get("decision", "")).upper() != "ESCALATE":
                raise HTTPException(400, "Alert is not an ESCALATE decision")
            alerts[i]["status"] = "escalate"
            alerts[i]["supervisor_approval"] = {
                "approved": True,
                "role": role,
            }
            save_alerts(alerts)
            # Audit entry
            from datetime import datetime, timezone

            append_audit(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event_type": "supervisor_approve",
                    "alert_id": alert_id,
                    "customer_id": a.get("customer_id"),
                    "customer_name": a.get("customer_name"),
                    "decision": "ESCALATE",
                    "reason": "Supervisor approval",
                }
            )
            return {"ok": True, "alert_id": alert_id}
    raise HTTPException(404, "Alert not found")


@app.get("/api/audit")
def audit_log():
    return load_audit()


@app.get("/api/audit/export")
def audit_export(format: str = "csv"):
    if format != "csv":
        raise HTTPException(400, "Only csv export supported")
    return PlainTextResponse(
        export_audit_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=lowtrans_audit.csv"},
    )


@app.get("/api/policy")
def policy(x_tenant: str | None = Header(default=None)):
    tid = _tenant(x_tenant)
    p = DATA_DIR / f"policy.{tid}.md"
    if p.exists():
        return {"content": p.read_text(encoding="utf-8"), "tenant": tid}
    return {"content": (DATA_DIR / "policy.md").read_text(encoding="utf-8"), "tenant": "default"}


@app.get("/api/policy/suggestions")
def policy_suggestions():
    return rag_engine.suggest_policy_refinement()


@app.get("/api/cases/{case_id}")
def get_resolved_case(case_id: str):
    for case in load_resolved_cases():
        if case["id"] == case_id:
            return case
    raise HTTPException(404, "Case not found")


@app.get("/api/alerts/{alert_id}/graph")
def get_alert_graph(alert_id: str):
    graph_path = DATA_DIR / "graphs" / f"{alert_id}.json"
    if not graph_path.exists():
        raise HTTPException(404, "Graph not available for this alert")
    with open(graph_path, encoding="utf-8") as f:
        return json.load(f)


@app.post("/api/demo/reset")
def demo_reset():
    count = reset_demo()
    return {"ok": True, "alerts_reset": count}


@app.get("/api/insights")
def insights():
    alerts = load_alerts()
    pending = sum(1 for a in alerts if a.get("status") == "pending")
    escalated = sum(1 for a in alerts if a.get("status") == "escalate")
    return {
        "vasps": [
            {
                "id": "vasp-summit",
                "name": "Summit Crypto Exchange",
                "status": "needs_attention" if escalated > 0 or pending > 3 else "healthy",
                "transactions_30d": 48200,
                "active_users": 12400,
                "approval_rate": 94.2,
                "pending_alerts": sum(
                    1
                    for a in alerts
                    if a.get("partner", "").startswith("Summit Crypto")
                    and a.get("status") == "pending"
                ),
                "risk_score": 72,
            },
            {
                "id": "vasp-retail",
                "name": "Summit Retail Group",
                "status": "needs_attention",
                "transactions_30d": 12800,
                "active_users": 3200,
                "approval_rate": 88.5,
                "pending_alerts": sum(
                    1
                    for a in alerts
                    if "Retail" in a.get("partner", "")
                    and a.get("status") == "pending"
                ),
                "risk_score": 81,
            },
            {
                "id": "vasp-nordic",
                "name": "Nordic Digital Assets",
                "status": "healthy",
                "transactions_30d": 22100,
                "active_users": 5600,
                "approval_rate": 97.1,
                "pending_alerts": 0,
                "risk_score": 34,
            },
            {
                "id": "vasp-pacific",
                "name": "Pacific On-Ramp Ltd",
                "status": "healthy",
                "transactions_30d": 8900,
                "active_users": 2100,
                "approval_rate": 96.8,
                "pending_alerts": 1,
                "risk_score": 41,
            },
        ],
        "summary": {
            "total_vasps": 4,
            "needs_attention": 2,
            "portfolio_approval_rate": 93.4,
            "pending_alerts": pending,
        },
    }


@app.get("/api/insights/activities")
def insights_activities():
    alerts = load_alerts()
    activities = []
    for a in alerts:
        if a.get("triage_result"):
            tr = a["triage_result"]
            activities.append({
                "id": f"act-{a['id']}-triage",
                "type": "triage",
                "title": f"Agent triage completed for {a['customer_name']}",
                "description": f"Decision: {tr['decision']} — {(tr['confidence'] * 100):.0f}% confidence",
                "alert_id": a["id"],
                "timestamp": tr.get("triaged_at", a.get("created_at")),
                "agent": "Transaction Monitoring Agent",
            })
        if a.get("risk_level") == "high" and a.get("status") == "pending":
            activities.append({
                "id": f"act-{a['id']}-flag",
                "type": "alert",
                "title": f"High-risk alert flagged: {a['id']}",
                "description": f"{a['customer_name']} — KYT {a['kyt_score']}, {', '.join(a.get('risk_tags', [])[:2])}",
                "alert_id": a["id"],
                "timestamp": a.get("created_at"),
                "agent": "Graph Analyst Agent",
            })
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    if len(activities) < 8:
        activities.extend([
            {
                "id": "act-policy-1",
                "type": "policy",
                "title": "RAG policy refinement suggested",
                "description": "Mixer exposure threshold may be lowered based on CASE-1205 pattern",
                "alert_id": None,
                "timestamp": "2025-07-06T08:00:00Z",
                "agent": "Rule Assistant Agent",
            },
            {
                "id": "act-batch-1",
                "type": "batch",
                "title": "Batch triage auto-cleared 9 of 12 alerts",
                "description": "RAG memory cited in 7 clear decisions",
                "alert_id": None,
                "timestamp": "2025-07-05T16:30:00Z",
                "agent": "Transaction Monitoring Agent",
            },
        ])
    return activities[:12]


@app.get("/api/stats")
def stats():
    alerts = load_alerts()
    pending = sum(1 for a in alerts if a.get("status") == "pending")
    cleared = sum(1 for a in alerts if a.get("status") == "clear")
    escalated = sum(1 for a in alerts if a.get("status") == "escalate")
    review = sum(1 for a in alerts if a.get("status") == "review")
    total_triaged = cleared + escalated + review
    return {
        "total_alerts": len(alerts),
        "pending": pending,
        "cleared": cleared,
        "escalated": escalated,
        "review": review,
        "auto_clear_rate": round(cleared / total_triaged * 100, 1) if total_triaged else 0,
        "rag_cases": len(rag_engine.cases),
        "db_connected": is_db_ready(),
        "agents": [a["name"] for a in list_agents()],
    }
