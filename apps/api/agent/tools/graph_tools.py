"""Graph investigation tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from db.repository import DATA_DIR, get_alert

GRAPHS_DIR = DATA_DIR / "graphs"


def read_graph(alert_id: str) -> dict[str, Any] | None:
    path = GRAPHS_DIR / f"{alert_id}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def summarize_graph(alert_id: str) -> dict[str, Any]:
    alert = get_alert(alert_id)
    graph = read_graph(alert_id)
    if not graph:
        sig = (alert or {}).get("signals", {})
        return {
            "summary": (
                f"No graph file for {alert_id}. "
                f"Signals: mixer={sig.get('mixer_exposure')}, "
                f"connections={(alert or {}).get('connections', 0)}"
            ),
            "flagged_node_ids": [],
            "node_count": 0,
        }
    flagged = graph.get("flagged_node_ids", [])
    nodes = graph.get("nodes", [])
    return {
        "summary": (
            f"Graph for {graph.get('customer_name', alert_id)}: "
            f"{len(nodes)} nodes, {len(graph.get('edges', []))} edges, "
            f"{len(flagged)} flagged."
        ),
        "flagged_node_ids": flagged,
        "node_count": len(nodes),
        "graph": graph,
    }
