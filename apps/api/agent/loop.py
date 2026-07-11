"""Agent loop — plan → tool calls → observe → decide (Bedrock Converse tools + fallback)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from agent.bedrock import converse_with_tools, is_configured
from agent.skills.handlers import dispatch_skill
from agent.skills.registry import get_skill, list_skills

OnStep = Callable[[dict[str, Any]], None] | None

# Skills safe to expose as LLM tools
LOOP_SKILLS = [
    "policy-qa",
    "rag-lookup",
    "sanctions-check",
    "osint-research",
    "kyb-verify",
    "kyt-score",
    "travel-rule-check",
    "graph-summary",
    "analyst-nl-sql",
    "sar-draft",
    "ml-validate",
    "ubo-unroll",
    "device-ip-check",
    "behavioral-patterns",
    "fiat-crypto-bridge",
    "audit-compile",
]

# Skills that share domain functions with the supervisor investigation engine
INVESTIGATION_SKILLS = [
    "sanctions-check",
    "osint-research",
    "kyb-verify",
    "ubo-unroll",
    "device-ip-check",
    "ml-validate",
    "kyt-score",
    "travel-rule-check",
    "graph-summary",
    "behavioral-patterns",
    "fiat-crypto-bridge",
    "rag-lookup",
    "sar-draft",
    "confidence-score",
    "audit-compile",
    "policy-qa",
    "sla-priority",
]


def skill_tool_specs(skill_ids: list[str] | None = None) -> list[dict[str, Any]]:
    ids = skill_ids or LOOP_SKILLS
    specs: list[dict[str, Any]] = []
    for sid in ids:
        skill = get_skill(sid)
        if not skill:
            continue
        specs.append(
            {
                "toolSpec": {
                    "name": sid.replace("-", "_"),
                    "description": skill.get("description") or skill.get("name") or sid,
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Analyst question or focus for this skill",
                                },
                                "alert_id": {
                                    "type": "string",
                                    "description": "Optional alert id override",
                                },
                            },
                            "required": ["query"],
                        }
                    },
                }
            }
        )
    return specs


def _tool_name_to_skill(name: str) -> str:
    return name.replace("_", "-")


def run_agent_loop(
    *,
    user_message: str,
    system: str,
    alert_id: str | None = None,
    skill_ids: list[str] | None = None,
    max_steps: int = 5,
    on_step: OnStep = None,
) -> dict[str, Any]:
    """Multi-step tool-calling loop. Falls back to single skill dispatch if Bedrock down."""
    tools = skill_tool_specs(skill_ids)
    tool_trace: list[dict[str, Any]] = []

    if not is_configured() or not tools:
        return _fallback_loop(user_message, alert_id, skill_ids, tool_trace, on_step)

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": [{"text": user_message}]},
    ]

    final_text = ""
    for step in range(max_steps):
        try:
            resp = converse_with_tools(
                messages=messages,
                system=system,
                tools=tools,
                max_tokens=2048,
                temperature=0.2,
            )
        except Exception:
            if tool_trace:
                break
            return _fallback_loop(user_message, alert_id, skill_ids, tool_trace, on_step)

        output_msg = resp.get("output", {}).get("message", {})
        content = output_msg.get("content") or []
        messages.append({"role": "assistant", "content": content})

        tool_uses = [c["toolUse"] for c in content if "toolUse" in c]
        texts = [c.get("text", "") for c in content if "text" in c]
        if texts:
            final_text = "\n".join(t for t in texts if t)

        if not tool_uses:
            break

        tool_results_content: list[dict[str, Any]] = []
        for tu in tool_uses:
            skill_id = _tool_name_to_skill(tu.get("name", ""))
            inp = tu.get("input") or {}
            query = str(inp.get("query") or user_message)
            aid = inp.get("alert_id") or alert_id
            payload = dispatch_skill(skill_id, query, aid)
            reply = payload.get("reply") or payload.get("summary") or json.dumps(
                {k: v for k, v in payload.items() if k != "cards"}, default=str
            )[:2000]
            trace = {
                "step": step + 1,
                "skill_id": skill_id,
                "query": query,
                "reply": reply[:500],
            }
            tool_trace.append(trace)
            if on_step:
                on_step(
                    {
                        "step": len(tool_trace),
                        "agent": "Agent Loop",
                        "skill_id": skill_id,
                        "status": "completed",
                        "input": f"{skill_id}: {query[:120]}",
                        "output": reply[:300],
                        "duration_ms": 80,
                        "workspace_link": None,
                    }
                )
            tool_results_content.append(
                {
                    "toolResult": {
                        "toolUseId": tu.get("toolUseId"),
                        "content": [{"text": str(reply)[:4000]}],
                        "status": "success",
                    }
                }
            )
        messages.append({"role": "user", "content": tool_results_content})

    if not final_text and tool_trace:
        final_text = tool_trace[-1].get("reply", "Investigation tools completed.")

    return {
        "reply": final_text or "No response.",
        "tool_trace": tool_trace,
        "loop_mode": "bedrock",
        "cards": [],
        "skills_available": [s["id"] for s in list_skills() if s["id"] in (skill_ids or LOOP_SKILLS)],
    }


def _fallback_loop(
    message: str,
    alert_id: str | None,
    skill_ids: list[str] | None,
    tool_trace: list[dict[str, Any]],
    on_step: OnStep,
) -> dict[str, Any]:
    """Keyword multi-skill path when Bedrock tools unavailable."""
    from agent.skills.registry import route_intent

    primary = route_intent(message, alert_id)
    allowed = set(skill_ids or LOOP_SKILLS)
    if primary not in allowed:
        primary = next(iter(allowed), "policy-qa")

    # Run primary + optional secondary for multi-hop feel
    sequence = [primary]
    lower = message.lower()
    if alert_id and primary == "graph-summary" and "sanctions-check" in allowed:
        sequence.append("sanctions-check")
    if alert_id and "sanction" in lower and "sanctions-check" in allowed and primary != "sanctions-check":
        if "sanctions-check" not in sequence:
            sequence.append("sanctions-check")
    if alert_id and any(w in lower for w in ("kyt", "score", "ml")) and "ml-validate" in allowed:
        sequence.insert(0, "ml-validate")
    if any(w in lower for w in ("similar", "precedent")) and "rag-lookup" in allowed and primary != "rag-lookup":
        sequence.append("rag-lookup")

    cards: list[Any] = []
    replies: list[str] = []
    extra: dict[str, Any] = {}
    for sid in sequence[:3]:
        payload = dispatch_skill(sid, message, alert_id)
        reply = payload.get("reply", "")
        replies.append(reply)
        cards.extend(payload.get("cards") or [])
        for key in ("visualization", "ml_score", "audit_pack", "graph", "flagged_node_ids", "exposure"):
            if key in payload:
                extra[key] = payload[key]
        tool_trace.append({"skill_id": sid, "query": message, "reply": reply[:500]})
        if on_step:
            on_step(
                {
                    "step": len(tool_trace),
                    "agent": "Agent Loop",
                    "skill_id": sid,
                    "status": "completed",
                    "input": sid,
                    "output": reply[:300],
                    "duration_ms": 40,
                    "workspace_link": None,
                }
            )

    return {
        "reply": "\n\n".join(r for r in replies if r),
        "tool_trace": tool_trace,
        "loop_mode": "fallback",
        "cards": cards,
        "skill_id": primary,
        "skill_name": (get_skill(primary) or {}).get("name", primary),
        **extra,
    }
