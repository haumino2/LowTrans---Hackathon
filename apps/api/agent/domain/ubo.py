"""UBO ownership unroller — input-varying mock corporate structure with risk flags.

Still simulated data, but the tree shape (depth, subsidiaries, ownership splits,
jurisdictions) is derived deterministically from the entity + transaction so no
two customers show an identical structure.
"""

from __future__ import annotations

from typing import Any

_OFFSHORE = ["Cayman Islands", "British Virgin Islands", "Seychelles", "Panama", "Marshall Islands"]
_NOMINEE = ["Passive Investor Pool A", "Nominee Trust Ltd", "Silverpeak Holdings", "Meridian Capital Partners", "Blue Harbor Trust"]


def _seed(entity_name: str) -> int:
    return sum(ord(c) for c in (entity_name or "entity"))


def unroll_ubo(entity_name: str, alert: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a 2–3 level ownership tree that varies by entity + transaction."""
    signals = (alert or {}).get("signals") or {}
    pep = bool(signals.get("pep_hit"))
    sanctions = bool(signals.get("sanctions_hit")) or str(
        ((alert or {}).get("sanctions_screening") or {}).get("status", "")
    ).lower() == "hit"
    partner = (alert or {}).get("partner") or "Summit Holdings LLC"
    country = (alert or {}).get("country") or "US"
    amount = float((alert or {}).get("amount_usd") or 0)
    tags = set((alert or {}).get("risk_tags") or [])

    seed = _seed(entity_name)
    # Larger / riskier transfers unroll deeper, more fragmented ownership.
    if amount >= 40000 or sanctions:
        depth, n_children = 3, 3
    elif amount >= 10000 or pep or "structuring" in tags:
        depth, n_children = 3, 2
    else:
        depth, n_children = 2, 1

    offshore_j = _OFFSHORE[seed % len(_OFFSHORE)]
    nominee_name = _NOMINEE[seed % len(_NOMINEE)]

    # Ownership split varies with the seed (keeps a controlling majority).
    controlling = 55 + (seed % 20)  # 55–74%
    remainder = round(100 - controlling, 1)

    natural_risk = "high" if (pep or sanctions) else "low"
    natural_flags = [f for f, on in (("PEP", pep), ("sanctions_proximity", sanctions)) if on]

    children: list[dict[str, Any]] = [
        {
            "name": entity_name,
            "type": "natural_person",
            "ownership_pct": float(controlling),
            "jurisdiction": country,
            "risk": natural_risk,
            "flags": natural_flags,
        }
    ]
    if n_children >= 2:
        offshore = pep or sanctions or amount >= 40000
        children.append(
            {
                "name": nominee_name,
                "type": "trust" if offshore else "llc",
                "ownership_pct": remainder,
                "jurisdiction": offshore_j if offshore else country,
                "risk": "elevated" if offshore else "low",
                "flags": ["offshore"] if offshore else [],
            }
        )
    if n_children >= 3:
        # Split the nominee stake again for a deeper layer.
        children[-1]["ownership_pct"] = round(remainder * 0.6, 1)
        children.append(
            {
                "name": f"{nominee_name} SPV",
                "type": "spv",
                "ownership_pct": round(remainder * 0.4, 1),
                "jurisdiction": offshore_j,
                "risk": "elevated" if (sanctions or pep) else "medium",
                "flags": ["shell_company"] if sanctions else [],
            }
        )

    holding = {
        "name": f"{partner} Holdings",
        "type": "llc",
        "ownership_pct": float(controlling),
        "jurisdiction": country,
        "risk": "medium" if (pep or amount >= 40000) else "low",
        "flags": [],
        "children": children,
    }

    root = {
        "name": partner,
        "type": "operating_company",
        "ownership_pct": 100.0,
        "jurisdiction": country,
        "risk": "high" if sanctions else ("medium" if pep else "low"),
        "flags": [],
        "children": [holding],
    }

    high_risk_nodes: list[dict[str, Any]] = []

    def walk(node: dict[str, Any], node_depth: int = 0) -> None:
        if node.get("risk") in ("high", "elevated") or node.get("flags"):
            high_risk_nodes.append(
                {
                    "name": node["name"],
                    "type": node["type"],
                    "depth": node_depth,
                    "risk": node.get("risk"),
                    "flags": node.get("flags") or [],
                }
            )
        for child in node.get("children") or []:
            walk(child, node_depth + 1)

    walk(root)

    return {
        "entity": entity_name,
        "depth": depth,
        "tree": root,
        "high_risk_nodes": high_risk_nodes,
        "summary": (
            f"UBO map for {entity_name}: {depth} levels, {len(children)} beneficial owner(s) via {partner} "
            f"(controlling {controlling}%). "
            + (
                f"{len(high_risk_nodes)} elevated node(s): "
                + ", ".join(n["name"] for n in high_risk_nodes[:3])
                if high_risk_nodes
                else "No nested high-risk UBO flagged."
            )
            + " [simulated]"
        ),
        "source": "simulated:ubo-unroller-v3",
    }
