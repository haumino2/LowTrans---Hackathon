"""RAG retrieval tools."""

from __future__ import annotations

from typing import Any

from agent.rag import rag_engine


def find_similar_cases(alert: dict[str, Any], top_k: int = 5) -> list[dict[str, Any]]:
    return rag_engine.find_similar(alert, top_k=top_k)


def suggest_policy() -> dict[str, Any]:
    return rag_engine.suggest_policy_refinement()
