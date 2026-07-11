"""Optional LangGraph investigation runtime with adaptive conditional edges."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, TypedDict

OnStep = Callable[[dict[str, Any]], None] | None


class GraphState(TypedDict, total=False):
    alert: dict[str, Any]
    investigation: Any
    emitter: Any
    result: dict[str, Any]
    on_step: Any
    nodes_completed: list[str]
    route: str


def langgraph_available() -> bool:
    try:
        from langgraph.graph import StateGraph  # noqa: F401

        return True
    except Exception:
        return False


def run_langgraph_investigation(
    alert: dict[str, Any],
    on_step: OnStep = None,
) -> dict[str, Any] | None:
    if os.getenv("LOWTRANS_USE_LANGGRAPH", "1").lower() in ("0", "false", "no"):
        return None
    if not langgraph_available():
        return None

    try:
        from langgraph.graph import END, START, StateGraph

        from agent.state import InvestigationState
        from agent.supervisor import (
            _Emitter,
            node_arbiter,
            node_identity,
            node_investigator,
            node_orchestrator,
        )

        def _boot(state: GraphState) -> GraphState:
            inv = InvestigationState(alert=state["alert"])
            emit = _Emitter(inv, state.get("on_step"), state["alert"].get("id", ""))
            return {
                **state,
                "investigation": inv,
                "emitter": emit,
                "nodes_completed": [],
                "route": "FULL",
            }

        def _orch(state: GraphState) -> GraphState:
            node_orchestrator(state["investigation"], state["emitter"])
            done = list(state.get("nodes_completed") or []) + ["orchestrator"]
            route = getattr(state["investigation"], "route", None) or "FULL"
            return {**state, "nodes_completed": done, "route": route}

        def _ident(state: GraphState) -> GraphState:
            lite = (state.get("route") or getattr(state["investigation"], "route", "")) == "STANDARD"
            node_identity(state["investigation"], state["emitter"], lite=lite)
            done = list(state.get("nodes_completed") or []) + ["entity-identity"]
            return {**state, "nodes_completed": done}

        def _invest(state: GraphState) -> GraphState:
            lite = (state.get("route") or getattr(state["investigation"], "route", "")) == "STANDARD"
            node_investigator(state["investigation"], state["emitter"], lite=lite)
            done = list(state.get("nodes_completed") or []) + ["financial-crime-investigator"]
            return {**state, "nodes_completed": done}

        def _arb(state: GraphState) -> GraphState:
            node_arbiter(state["investigation"], state["emitter"])
            done = list(state.get("nodes_completed") or []) + ["arbiter"]
            result = state["investigation"].to_result()
            result["runtime"] = "langgraph"
            result["graph_nodes"] = done
            return {**state, "nodes_completed": done, "result": result}

        def _route_after_orch(state: GraphState) -> str:
            """Conditional edge: FAST_TRACK skips Identity + Investigator."""
            route = state.get("route") or getattr(state.get("investigation"), "route", None) or "FULL"
            if route == "FAST_TRACK":
                return "arbiter"
            return "entity_identity"

        g = StateGraph(GraphState)
        g.add_node("boot", _boot)
        g.add_node("orchestrator", _orch)
        g.add_node("entity_identity", _ident)
        g.add_node("investigator", _invest)
        g.add_node("arbiter", _arb)
        g.add_edge(START, "boot")
        g.add_edge("boot", "orchestrator")
        g.add_conditional_edges(
            "orchestrator",
            _route_after_orch,
            {
                "arbiter": "arbiter",
                "entity_identity": "entity_identity",
            },
        )
        g.add_edge("entity_identity", "investigator")
        g.add_edge("investigator", "arbiter")
        g.add_edge("arbiter", END)
        app = g.compile()
        out = app.invoke({"alert": alert, "on_step": on_step})
        result = out.get("result")
        return result if isinstance(result, dict) else None
    except Exception:
        return None
