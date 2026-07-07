"""Data access — Postgres when available, JSON files as fallback."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from db.models import (
    AlertRow,
    AuditRow,
    CopilotSessionRow,
    ResolvedCaseRow,
    TransactionRow,
    get_session,
    is_db_ready,
)

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _load_json_alerts() -> list[dict[str, Any]]:
    with open(DATA_DIR / "alerts.json", encoding="utf-8") as f:
        return json.load(f)


def _save_json_alerts(alerts: list[dict[str, Any]]) -> None:
    with open(DATA_DIR / "alerts.json", "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2)


def load_alerts() -> list[dict[str, Any]]:
    if is_db_ready():
        session = get_session()
        try:
            rows = session.query(AlertRow).all()
            return [r.data for r in rows]
        finally:
            session.close()
    return _load_json_alerts()


def save_alerts(alerts: list[dict[str, Any]]) -> None:
    if is_db_ready():
        session = get_session()
        try:
            for a in alerts:
                row = session.get(AlertRow, a["id"])
                if row:
                    row.data = a
                    row.status = a.get("status", "pending")
                    row.updated_at = datetime.utcnow()
                else:
                    session.add(
                        AlertRow(
                            id=a["id"],
                            data=a,
                            status=a.get("status", "pending"),
                        )
                    )
            session.commit()
        finally:
            session.close()
    else:
        _save_json_alerts(alerts)


def get_alert(alert_id: str) -> dict[str, Any] | None:
    for a in load_alerts():
        if a["id"] == alert_id:
            return a
    return None


def load_resolved_cases() -> list[dict[str, Any]]:
    if is_db_ready():
        session = get_session()
        try:
            return [r.data for r in session.query(ResolvedCaseRow).all()]
        finally:
            session.close()
    with open(DATA_DIR / "resolved_cases.json", encoding="utf-8") as f:
        return json.load(f)


def load_audit() -> list[dict[str, Any]]:
    if is_db_ready():
        session = get_session()
        try:
            rows = (
                session.query(AuditRow)
                .order_by(AuditRow.created_at.desc())
                .all()
            )
            return [r.data for r in rows]
        finally:
            session.close()
    path = DATA_DIR / "audit_log.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return list(reversed(entries))


def append_audit(entry: dict[str, Any]) -> None:
    if is_db_ready():
        session = get_session()
        try:
            session.add(AuditRow(data=entry))
            session.commit()
        finally:
            session.close()
    else:
        path = DATA_DIR / "audit_log.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


def save_copilot_turn(
    session_id: str,
    message: str,
    response: dict[str, Any],
    alert_id: str | None = None,
) -> None:
    entry = {
        "session_id": session_id,
        "alert_id": alert_id,
        "message": message,
        "response": response,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if is_db_ready():
        session = get_session()
        try:
            session.add(CopilotSessionRow(session_id=session_id, alert_id=alert_id, data=entry))
            session.commit()
        finally:
            session.close()
    else:
        path = DATA_DIR / "copilot_sessions.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


def load_copilot_sessions(session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    if is_db_ready():
        session = get_session()
        try:
            rows = (
                session.query(CopilotSessionRow)
                .filter(CopilotSessionRow.session_id == session_id)
                .order_by(CopilotSessionRow.created_at.desc())
                .limit(limit)
                .all()
            )
            return [r.data for r in reversed(rows)]
        finally:
            session.close()
    path = DATA_DIR / "copilot_sessions.jsonl"
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                if row.get("session_id") == session_id:
                    out.append(row)
    return out[-limit:]


def export_audit_csv() -> str:
    entries = load_audit()
    if not entries:
        return "timestamp,event_type,alert_id,customer_name,decision\n"
    keys = [
        "timestamp",
        "event_type",
        "alert_id",
        "customer_name",
        "decision",
        "reason",
        "confidence",
        "role",
        "model_id",
        "rag_backend",
        "skill_id",
        "session_id",
    ]
    lines = [",".join(keys)]
    for e in entries:
        lines.append(",".join(f'"{str(e.get(k, "")).replace(chr(34), chr(39))}"' for k in keys))
    return "\n".join(lines)


def reset_demo() -> int:
    alerts = load_alerts()
    for a in alerts:
        a["status"] = "pending"
        a.pop("triage_result", None)
        a.pop("override", None)
        a.pop("supervisor_approval", None)
        a.pop("assigned_to", None)
        a.pop("notes", None)
        a.pop("case_id", None)
        a.pop("case_state", None)
        a.pop("case_assigned_to", None)
        a.pop("case_notes", None)
    save_alerts(alerts)
    if is_db_ready():
        session = get_session()
        try:
            session.query(AuditRow).delete()
            session.commit()
        finally:
            session.close()
    else:
        audit_path = DATA_DIR / "audit_log.jsonl"
        if audit_path.exists():
            audit_path.write_text("", encoding="utf-8")
    return len(alerts)


def run_sql_query(sql: str) -> tuple[list[str], list[list[Any]]]:
    """Execute read-only SQL for Data Analyst."""
    if not is_db_ready():
        raise RuntimeError("Database required for analyst queries")
    session = get_session()
    try:
        result = session.execute(__import__("sqlalchemy").text(sql))
        columns = list(result.keys())
        rows = [list(r) for r in result.fetchall()]
        return columns, rows
    finally:
        session.close()


def get_analyst_schema() -> str:
    from db.models import is_sqlite

    bool_type = "INTEGER" if is_sqlite() else "BOOLEAN"
    return f"""
TABLE transactions (
  id INTEGER PRIMARY KEY,
  alert_id VARCHAR,
  customer_id VARCHAR,
  customer_name VARCHAR,
  partner VARCHAR,
  asset VARCHAR,
  network VARCHAR,
  direction VARCHAR,
  amount_usd REAL,
  kyt_score INTEGER,
  risk_level VARCHAR,
  travel_rule_status VARCHAR,
  country VARCHAR,
  rules_fired_count INTEGER,
  mixer_exposure {bool_type},
  sanctions_hit {bool_type},
  created_at TIMESTAMP
)
""".strip()
