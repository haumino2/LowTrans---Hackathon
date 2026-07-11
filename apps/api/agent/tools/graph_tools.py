"""Graph investigation tools."""

from __future__ import annotations

import json
from collections import deque
from typing import Any

from db.repository import DATA_DIR, get_alert

GRAPHS_DIR = DATA_DIR / "graphs"

NO_EXPOSURE_MSG = "No on-chain exposure to flagged entities detected"


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


def _primary_wallet_id(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str | None:
    """Prefer the wallet owned by a customer node; else first wallet."""
    by_id = {n["id"]: n for n in nodes if n.get("id")}
    for e in edges:
        src, tgt = e.get("source"), e.get("target")
        src_n, tgt_n = by_id.get(src), by_id.get(tgt)
        if not src_n or not tgt_n:
            continue
        if src_n.get("type") == "customer" and tgt_n.get("type") == "wallet":
            return str(tgt)
        if tgt_n.get("type") == "customer" and src_n.get("type") == "wallet":
            return str(src)
    for n in nodes:
        if n.get("type") == "wallet" and n.get("id"):
            return str(n["id"])
    return None


def _is_risk_flagged(node: dict[str, Any], origin_id: str | None) -> bool:
    """Flagged = mixer / SDN / high-risk counterparty (not the origin wallet)."""
    nid = str(node.get("id") or "")
    if origin_id and nid == origin_id:
        return False
    ntype = str(node.get("type") or "").lower()
    if ntype in ("customer",):
        return False
    label = str(node.get("label") or "")
    subtitle = str(node.get("subtitle") or "")
    blob = f"{nid} {label} {subtitle}".lower()
    if ntype == "mixer":
        return True
    if "sdn" in blob or "ofac" in blob:
        return True
    if ntype == "counterparty" and str(node.get("risk") or "").lower() == "high":
        return True
    return False


def _edge_amount(edge: dict[str, Any] | None) -> float:
    if not edge:
        return 0.0
    raw = edge.get("amount_usd")
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def compute_exposure(alert_id: str) -> dict[str, Any]:
    """BFS from primary wallet; sum direct/indirect USD exposure to flagged entities."""
    graph = read_graph(alert_id)
    empty: dict[str, Any] = {
        "direct_exposure": 0.0,
        "indirect_exposure": 0.0,
        "min_indirect_hops": None,
        "paths": [],
        "flagged_reached": [],
        "origin_wallet": None,
        "has_graph": False,
        "summary": NO_EXPOSURE_MSG,
    }
    if not graph:
        return empty

    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])
    by_id = {str(n["id"]): n for n in nodes if n.get("id")}
    origin = _primary_wallet_id(nodes, edges)
    if not origin or origin not in by_id:
        return {**empty, "has_graph": True, "summary": NO_EXPOSURE_MSG}

    # Undirected adjacency with edge payload for hop traversal
    adj: dict[str, list[tuple[str, dict[str, Any]]]] = {nid: [] for nid in by_id}
    for e in edges:
        s, t = e.get("source"), e.get("target")
        if s in adj and t in adj:
            adj[s].append((t, e))
            adj[t].append((s, e))

    # BFS: distance, parent, inbound edge from parent
    dist: dict[str, int] = {origin: 0}
    parent: dict[str, str | None] = {origin: None}
    inbound: dict[str, dict[str, Any] | None] = {origin: None}
    q: deque[str] = deque([origin])
    while q:
        cur = q.popleft()
        for nxt, edge in adj.get(cur, []):
            if nxt in dist:
                continue
            dist[nxt] = dist[cur] + 1
            parent[nxt] = cur
            inbound[nxt] = edge
            q.append(nxt)

    def _path_nodes(target: str) -> list[str]:
        chain: list[str] = []
        cur: str | None = target
        while cur is not None:
            chain.append(cur)
            cur = parent.get(cur)
        chain.reverse()
        return chain

    def _path_labels(node_ids: list[str]) -> list[str]:
        out = []
        for nid in node_ids:
            n = by_id.get(nid, {})
            out.append(str(n.get("label") or nid))
        return out

    direct = 0.0
    indirect = 0.0
    min_indirect_hops: int | None = None
    paths: list[dict[str, Any]] = []
    flagged_reached: list[str] = []

    for nid, node in by_id.items():
        if nid not in dist or not _is_risk_flagged(node, origin):
            continue
        hops = dist[nid]
        if hops < 1:
            continue
        amt = _edge_amount(inbound.get(nid))
        node_ids = _path_nodes(nid)
        labels = _path_labels(node_ids)
        entry = {
            "node_id": nid,
            "label": str(node.get("label") or nid),
            "type": node.get("type"),
            "risk": node.get("risk"),
            "hops": hops,
            "amount_usd": amt,
            "path": node_ids,
            "path_labels": labels,
        }
        paths.append(entry)
        flagged_reached.append(nid)
        if hops == 1:
            direct += amt
        else:
            indirect += amt
            min_indirect_hops = hops if min_indirect_hops is None else min(min_indirect_hops, hops)

    paths.sort(key=lambda p: (p["hops"], -float(p["amount_usd"] or 0)))

    if not paths:
        summary = NO_EXPOSURE_MSG
    else:
        bits: list[str] = []
        bits.append(f"Direct ${direct:,.0f}")
        if min_indirect_hops is not None:
            bits.append(f"indirect ${indirect:,.0f} (min {min_indirect_hops}-hop)")
        else:
            bits.append("indirect $0")
        hop_bits = []
        for p in paths[:4]:
            hop_bits.append(f"{p['hops']}-hop → {p['label']} (${p['amount_usd']:,.0f})")
        summary = (
            f"On-chain exposure: {'; '.join(bits)}. "
            + ("Paths: " + "; ".join(hop_bits) if hop_bits else "")
        ).strip()

    return {
        "direct_exposure": round(direct, 2),
        "indirect_exposure": round(indirect, 2),
        "min_indirect_hops": min_indirect_hops,
        "paths": paths,
        "flagged_reached": flagged_reached,
        "origin_wallet": origin,
        "has_graph": True,
        "summary": summary[:320],
    }
