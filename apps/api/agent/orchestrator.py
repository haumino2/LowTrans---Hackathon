"""Workflow orchestrator — LangGraph when available, else 4-node supervisor."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent.graph_runtime import run_langgraph_investigation
from agent.supervisor import run_investigation

WORKSPACE_LINKS = {
    "Orchestrator": "/cases/{alert_id}?tab=Timeline",
    "Entity Identity Agent": "/copilot?alert_id={alert_id}&q=screening",
    "Financial Crime Investigator": "/cases/{alert_id}?tab=Connections+Graph",
    "Arbiter": "/cases/{alert_id}?tab=Overview&sar=1",
}


def run_workflow(
    alert: dict[str, Any],
    on_step: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Execute investigation graph; prefer LangGraph runtime when installed."""
    lg = run_langgraph_investigation(alert, on_step=on_step)
    if lg:
        return lg
    return run_investigation(alert, on_step=on_step)
