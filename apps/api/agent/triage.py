"""LowTrans triage agent — delegates to workflow orchestrator."""

from __future__ import annotations

import time
from collections.abc import Generator
from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Thread
from typing import Any

from agent.orchestrator import run_workflow
from agent.bedrock import health_check as bedrock_health
from agent.rag import rag_engine
from db.repository import append_audit


def triage_alert(alert: dict[str, Any], on_step=None) -> dict[str, Any]:
    result = run_workflow(alert, on_step=on_step)
    result["alert_id"] = alert["id"]
    result["triaged_at"] = datetime.now(timezone.utc).isoformat()
    _write_audit(alert, result)
    return result


def triage_all_pending(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pending = [a for a in alerts if a.get("status") == "pending"]
    return [triage_alert(a) for a in pending]


def stream_triage_events(
    alert: dict[str, Any],
    step_delay_ms: int = 350,
) -> Generator[dict[str, Any], None, None]:
    """Yield step events then final result for SSE."""
    queue: Queue[dict[str, Any]] = Queue()

    def on_step(step: dict[str, Any]) -> None:
        time.sleep(step_delay_ms / 1000.0)
        queue.put({"event": "step", "step": step})

    def worker() -> None:
        try:
            result = triage_alert(alert, on_step=on_step)
            queue.put({"event": "complete", "result": result})
        except Exception as e:
            queue.put({"event": "error", "message": str(e)})

    Thread(target=worker, daemon=True).start()

    while True:
        try:
            item = queue.get(timeout=120)
        except Empty:
            yield {"event": "error", "message": "Workflow timeout"}
            break
        yield item
        if item.get("event") in ("complete", "error"):
            break


def _write_audit(alert: dict[str, Any], result: dict[str, Any]) -> None:
    bedrock = bedrock_health(live=False)
    entry = {
        "timestamp": result["triaged_at"],
        "event_type": "triage",
        "alert_id": alert["id"],
        "customer_id": alert["customer_id"],
        "customer_name": alert["customer_name"],
        "decision": result["decision"],
        "confidence": result["confidence"],
        "agents_used": result["agents_used"],
        "disposition": result["suggested_disposition"],
        "rag_cases": [s["case_id"] for s in result.get("similar_cases", [])],
        "rag_backend": rag_engine.backend,
        "model_id": bedrock.get("model_id"),
        "workflow_steps": len(result.get("workflow_steps", [])),
        "total_duration_ms": result.get("workflow_summary", {}).get("total_duration_ms", 0),
    }
    append_audit(entry)


def write_override_audit(alert: dict[str, Any], decision: str, reason: str, role: str | None = None) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "override",
        "alert_id": alert["id"],
        "customer_id": alert["customer_id"],
        "customer_name": alert["customer_name"],
        "decision": decision,
        "reason": reason,
        "role": role,
        "previous_decision": (alert.get("triage_result") or {}).get("decision"),
    }
    append_audit(entry)
