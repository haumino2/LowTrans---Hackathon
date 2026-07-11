"""AML Copilot — Orchestrator entry; agent loop with skill tools."""

from __future__ import annotations

from typing import Any

from agent.loop import INVESTIGATION_SKILLS, LOOP_SKILLS, run_agent_loop
from agent.skills.registry import get_skill
from db.repository import save_copilot_turn

ORCHESTRATOR_SYSTEM = """You are the LowTrans Orchestrator (AML investigation supervisor).
Route analyst questions by calling the right skills/tools.
When alert_id is present, prefer the same investigation skills as case triage:
sanctions-check, graph-summary (on-chain exposure), ml-validate, kyt-score,
behavioral-patterns, fiat-crypto-bridge, rag-lookup, sar-draft.
Do NOT use analyst-nl-sql for mixer/exposure questions on an open alert — use graph-summary.
Be concise. Cite tool outputs. Never override a confirmed OFAC/sanctions hit with CLEAR.
"""


def handle_copilot(
    message: str,
    alert_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    # With alert context, use the same skill set as the supervisor investigation engine
    # so copilot and triage share domain logic (no NL-SQL divergence on open cases).
    skill_ids = INVESTIGATION_SKILLS if alert_id else LOOP_SKILLS
    loop_result = run_agent_loop(
        user_message=message if not alert_id else f"[alert_id={alert_id}] {message}",
        system=ORCHESTRATOR_SYSTEM,
        alert_id=alert_id,
        skill_ids=skill_ids,
        max_steps=5,
    )
    skill_id = loop_result.get("skill_id") or (
        (loop_result.get("tool_trace") or [{}])[0].get("skill_id") if loop_result.get("tool_trace") else "orchestrator"
    )
    skill = get_skill(skill_id) if skill_id else None
    result: dict[str, Any] = {
        "skill_id": skill_id or "orchestrator",
        "skill_name": (skill or {}).get("name", "Orchestrator Loop"),
        "alert_id": alert_id,
        "session_id": session_id,
        "reply": loop_result.get("reply", ""),
        "cards": loop_result.get("cards", []),
        "tool_trace": loop_result.get("tool_trace", []),
        "loop_mode": loop_result.get("loop_mode", "fallback"),
        "type": "copilot",
    }
    # Preserve visualization / exposure payloads from skill dispatch
    for key in ("visualization", "ml_score", "audit_pack", "graph", "flagged_node_ids", "exposure"):
        if key in loop_result:
            result[key] = loop_result[key]

    save_copilot_turn(
        session_id=session_id or f"default-{alert_id or 'global'}",
        alert_id=alert_id,
        message=message,
        response=result,
    )
    return result
