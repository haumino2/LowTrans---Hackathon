"""AML Copilot — routes user messages to registered skills."""

from __future__ import annotations

from typing import Any

from agent.skills.handlers import dispatch_skill
from agent.skills.registry import get_skill, route_intent
from db.repository import save_copilot_turn


def handle_copilot(
    message: str,
    alert_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    skill_id = route_intent(message, alert_id)
    skill = get_skill(skill_id) or {"id": skill_id, "name": skill_id}
    payload = dispatch_skill(skill_id, message, alert_id)
    result: dict[str, Any] = {
        "skill_id": skill_id,
        "skill_name": skill.get("name", skill_id),
        "alert_id": alert_id,
        "session_id": session_id,
        "cards": payload.get("cards", []),
        **{k: v for k, v in payload.items() if k != "cards"},
    }
    save_copilot_turn(
        session_id=session_id or f"default-{alert_id or 'global'}",
        alert_id=alert_id,
        message=message,
        response=result,
    )
    return result
