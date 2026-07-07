"""Skill registry — Agent → Skills → Tools."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

REGISTRY_PATH = Path(__file__).resolve().parent / "registry.yaml"


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_agents() -> list[dict[str, Any]]:
    return load_registry().get("agents", [])


def list_skills() -> list[dict[str, Any]]:
    return load_registry().get("skills", [])


def get_agent(agent_id: str) -> dict[str, Any] | None:
    for agent in list_agents():
        if agent["id"] == agent_id:
            return agent
    return None


def get_skill(skill_id: str) -> dict[str, Any] | None:
    for skill in list_skills():
        if skill["id"] == skill_id:
            return skill
    return None


def route_intent(message: str, alert_id: str | None = None) -> str:
    """Simple keyword router — picks skill for copilot."""
    lower = message.lower()
    analyst_kw = (
        "sql", "query", "count", "how many", "average", "top", "fire rate",
        "transactions", "breakdown", "mixer", "exposure", "partner", "kyt",
        "volume", "show", "list", "highest", "lowest", "total", "analytics",
        "by partner", "by risk", "withdrawal", "deposit",
    )
    if any(w in lower for w in analyst_kw):
        return "analyst-nl-sql"
    if any(w in lower for w in ("similar", "precedent", "past case", "rag", "history")):
        return "rag-lookup"
    if any(w in lower for w in ("sar", "narrative", "filing", "suspicious activity")):
        return "sar-draft"
    if any(w in lower for w in ("policy", "threshold", "auto-clear", "aml policy")):
        return "policy-qa"
    if alert_id and any(w in lower for w in ("graph", "mixer", "connection", "on-chain")):
        return "graph-summary"
    if alert_id and any(w in lower for w in ("sanction", "ofac", "pep", "screening")):
        return "sanctions-check"
    if any(w in lower for w in ("osint", "research", "entity", "adverse media", "company")):
        return "osint-research"
    if any(w in lower for w in ("kyb", "due diligence", "business verify", "vasp partner")):
        return "kyb-verify"
    if any(w in lower for w in ("suggest rule", "rule build", "monitoring rule", "new rule")):
        return "rule-build"
    return "policy-qa"
