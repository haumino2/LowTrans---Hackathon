"""SQL tools — NL generation + read-only execution."""

from __future__ import annotations

from typing import Any

from agent.analyst import analyze_question
from agent.analyst import generate_sql as _generate_sql
from agent.analyst import run_analyst_query


def generate_sql(question: str) -> dict[str, Any]:
    return _generate_sql(question)


def run_sql(sql: str) -> dict[str, Any]:
    """Execute read-only SQL; returns the analyst result dict as-is."""
    return run_analyst_query(sql)


def explain_sql(question: str) -> dict[str, Any]:
    return analyze_question(question)
