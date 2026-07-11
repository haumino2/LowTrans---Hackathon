"""Data Analyst — NL to SQL with read-only guardrails."""

from __future__ import annotations

import re
from typing import Any

from agent.bedrock import invoke_claude, is_configured
from agent.viz import build_visualization
from db.models import is_db_ready, is_sqlite
from db.repository import get_analyst_schema, run_sql_query

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)
_HAS_LIMIT = re.compile(r"\bLIMIT\s+\d+", re.IGNORECASE)
_DEFAULT_LIMIT = 100


def sql_dialect() -> str:
    """Dialect for generated SQL. JSON demo mode uses in-memory SQLite."""
    if not is_db_ready() or is_sqlite():
        return "SQLite"
    return "PostgreSQL"


def _validate_sql(sql: str) -> str | None:
    cleaned = sql.strip().rstrip(";")
    if not cleaned.upper().startswith("SELECT"):
        return "Only SELECT queries are allowed"
    if _FORBIDDEN.search(cleaned):
        return "Query contains forbidden keywords"
    if ";" in cleaned:
        return "Multiple statements not allowed"
    return None


def _ensure_limit(sql: str, default: int = _DEFAULT_LIMIT) -> str:
    cleaned = sql.strip().rstrip(";")
    if _HAS_LIMIT.search(cleaned):
        return cleaned
    return f"{cleaned} LIMIT {default}"


def _mock_sql(question: str, dialect: str | None = None) -> tuple[str, str]:
    """Rule-based SQL when Bedrock is throttled."""
    dialect = dialect or sql_dialect()
    q = question.lower()
    if dialect == "SQLite":
        since_30d = "DATE('now', '-30 day')"
    else:
        since_30d = "NOW() - INTERVAL '30 days'"

    if "mixer" in q:
        sql = (
            "SELECT partner, COUNT(*) AS cnt, AVG(kyt_score) AS avg_kyt "
            "FROM transactions WHERE mixer_exposure = 1 "
            "GROUP BY partner ORDER BY cnt DESC LIMIT 10"
        )
        expl = "Mixer exposure counts by partner (mock SQL — Bedrock unavailable)."
    elif "fire rate" in q or "rule" in q:
        sql = (
            "SELECT risk_level, AVG(rules_fired_count) AS avg_rules, COUNT(*) AS tx_count "
            "FROM transactions GROUP BY risk_level ORDER BY avg_rules DESC"
        )
        expl = "Average rules fired by risk level."
    elif "partner" in q and ("kyt" in q or "high" in q):
        sql = (
            "SELECT partner, COUNT(*) AS tx_count, AVG(kyt_score) AS avg_kyt "
            "FROM transactions WHERE kyt_score > 50 "
            "GROUP BY partner ORDER BY tx_count DESC LIMIT 10"
        )
        expl = "High-KYT transaction counts by partner."
    elif "high" in q and ("risk" in q or "kyt" in q):
        sql = (
            "SELECT customer_name, asset, amount_usd, kyt_score, created_at "
            "FROM transactions WHERE kyt_score > 65 "
            "ORDER BY kyt_score DESC LIMIT 20"
        )
        expl = "Top high-KYT transactions."
    elif "travel" in q:
        sql = (
            "SELECT travel_rule_status, COUNT(*) AS cnt, SUM(amount_usd) AS volume "
            "FROM transactions GROUP BY travel_rule_status"
        )
        expl = "Travel Rule status breakdown."
    elif "trend" in q or "daily" in q:
        sql = (
            "SELECT DATE(created_at) AS day, COUNT(*) AS tx_count, SUM(amount_usd) AS volume, AVG(kyt_score) AS avg_kyt "
            "FROM transactions "
            f"WHERE created_at >= {since_30d} "
            "GROUP BY DATE(created_at) ORDER BY day ASC"
        )
        expl = "30-day daily trend (count, volume, avg KYT)."
    elif "outlier" in q or ("top" in q and "withdrawal" in q and "amount" in q):
        sql = (
            "SELECT customer_name, partner, asset, amount_usd, kyt_score, created_at "
            "FROM transactions WHERE direction = 'withdrawal' "
            "ORDER BY amount_usd DESC, kyt_score DESC LIMIT 20"
        )
        expl = "Top 20 withdrawal outliers by amount (with KYT)."
    else:
        sql = (
            "SELECT partner, COUNT(*) AS tx_count, AVG(kyt_score) AS avg_kyt, "
            "SUM(amount_usd) AS total_volume FROM transactions "
            "GROUP BY partner ORDER BY total_volume DESC"
        )
        expl = "Transaction summary by partner (default analyst query)."
    return sql, expl


def generate_sql(question: str) -> dict[str, Any]:
    schema = get_analyst_schema()
    dialect = sql_dialect()
    sql = ""
    explanation = ""

    if is_configured():
        try:
            date_hint = (
                "DATE('now', '-N day')"
                if dialect == "SQLite"
                else "NOW() - INTERVAL 'N days'"
            )
            raw = invoke_claude(
                f"Question: {question}\n\nReturn ONLY valid {dialect} SELECT SQL, no markdown.",
                system=(
                    f"You are a Data Analyst for crypto AML. Generate a single read-only {dialect} "
                    f"SELECT query using ONLY this schema:\n{schema}\n"
                    "No INSERT/UPDATE/DELETE. No comments. One statement only. "
                    f"Use {dialect} date/time functions (e.g. {date_hint}). "
                    f"Include LIMIT (default {_DEFAULT_LIMIT}) unless aggregating a small dimension."
                ),
                max_tokens=512,
                temperature=0.0,
            )
            sql = raw.strip().strip("`")
            if sql.lower().startswith("sql"):
                sql = sql.split("\n", 1)[-1].strip()
            explanation = f"Generated via Bedrock Nova ({dialect})."
        except Exception:
            sql, explanation = _mock_sql(question, dialect)
    else:
        sql, explanation = _mock_sql(question, dialect)

    err = _validate_sql(sql)
    if err:
        return {"sql": sql, "explanation": explanation, "blocked": True, "error": err}

    sql = _ensure_limit(sql)
    return {"sql": sql, "explanation": explanation, "blocked": False, "dialect": dialect}


def run_analyst_query(sql: str) -> dict[str, Any]:
    err = _validate_sql(sql)
    if err:
        raise ValueError(err)
    sql = _ensure_limit(sql)
    columns, rows = run_sql_query(sql)
    serializable = []
    for row in rows:
        serializable.append(
            [c.isoformat() if hasattr(c, "isoformat") else c for c in row]
        )
    return {
        "sql": sql,
        "columns": columns,
        "rows": serializable,
        "row_count": len(serializable),
    }


def analyze_question(question: str) -> dict[str, Any]:
    """Generate SQL, run it, and return visualization-ready payload."""
    preview = generate_sql(question)
    if preview.get("blocked"):
        return preview
    try:
        data = run_analyst_query(preview["sql"])
        viz = build_visualization(
            question=question,
            columns=data["columns"],
            rows=data["rows"],
            explanation=preview.get("explanation", ""),
        )
        return {
            "sql": preview["sql"],
            "explanation": preview["explanation"],
            "columns": data["columns"],
            "rows": data["rows"],
            "row_count": data["row_count"],
            "visualization": viz,
        }
    except Exception as exc:
        return {
            "sql": preview.get("sql", ""),
            "explanation": preview.get("explanation", ""),
            "error": str(exc),
        }
