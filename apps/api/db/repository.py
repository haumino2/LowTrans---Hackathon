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


def _is_demo_hero(alert: dict[str, Any]) -> bool:
    """Hero alerts used by Demo Mode — flagged at seed, or legacy ALT-3001..3012."""
    if alert.get("demo_hero") is True:
        return True
    alert_id = str(alert.get("id") or "")
    if alert_id.startswith("ALT-30") and len(alert_id) == 8:
        # ALT-3001 … ALT-3012 (legacy JSON without demo_hero)
        try:
            n = int(alert_id.split("-")[1])
            return 3001 <= n <= 3012
        except ValueError:
            return False
    return False


def reset_demo() -> int:
    """Reset only demo hero alerts to pending; leave synthetic history intact."""
    alerts = load_alerts()
    reset_count = 0
    for a in alerts:
        if not _is_demo_hero(a):
            continue
        a["demo_hero"] = True
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
        reset_count += 1
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
    return reset_count


def _alert_to_tx_tuple(alert: dict[str, Any], row_id: int) -> tuple[Any, ...]:
    """Map an alerts.json record onto the analyst transactions schema."""
    signals = alert.get("signals") or {}
    created = alert.get("created_at") or ""
    if isinstance(created, str) and created.endswith("Z"):
        created = created.replace("Z", "+00:00")
    return (
        row_id,
        alert.get("id"),
        alert.get("customer_id") or "",
        alert.get("customer_name") or "",
        alert.get("partner") or "",
        alert.get("asset") or "",
        alert.get("network") or "",
        alert.get("direction") or "",
        float(alert.get("amount_usd") or 0),
        int(alert.get("kyt_score") or 0),
        alert.get("risk_level") or "",
        alert.get("travel_rule_status") or "",
        alert.get("country") or "",
        len(alert.get("rules_fired") or []),
        1 if signals.get("mixer_exposure") else 0,
        1 if signals.get("sanctions_hit") else 0,
        alert.get("segment"),
        alert.get("product"),
        alert.get("rail"),
        created,
    )


def run_sql_on_alerts_json(sql: str) -> tuple[list[str], list[list[Any]]]:
    """Read-only analyst queries against alerts.json via in-memory SQLite."""
    import sqlite3

    alerts = _load_json_alerts()
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(
            """
            CREATE TABLE transactions (
              id INTEGER PRIMARY KEY,
              alert_id TEXT,
              customer_id TEXT,
              customer_name TEXT,
              partner TEXT,
              asset TEXT,
              network TEXT,
              direction TEXT,
              amount_usd REAL,
              kyt_score INTEGER,
              risk_level TEXT,
              travel_rule_status TEXT,
              country TEXT,
              rules_fired_count INTEGER,
              mixer_exposure INTEGER,
              sanctions_hit INTEGER,
              segment TEXT,
              product TEXT,
              rail TEXT,
              created_at TEXT
            )
            """
        )
        rows = [_alert_to_tx_tuple(a, i + 1) for i, a in enumerate(alerts)]
        conn.executemany(
            """
            INSERT INTO transactions (
              id, alert_id, customer_id, customer_name, partner, asset, network,
              direction, amount_usd, kyt_score, risk_level, travel_rule_status,
              country, rules_fired_count, mixer_exposure, sanctions_hit,
              segment, product, rail, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        return columns, [list(r) for r in cur.fetchall()]
    finally:
        conn.close()


def run_sql_query(sql: str) -> tuple[list[str], list[list[Any]]]:
    """Execute read-only SQL for Data Analyst. Falls back to alerts.json when DB is down."""
    if not is_db_ready():
        return run_sql_on_alerts_json(sql)
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

    # Demo JSON mode queries via in-memory SQLite — match that dialect.
    use_sqlite = (not is_db_ready()) or is_sqlite()
    bool_type = "INTEGER" if use_sqlite else "BOOLEAN"
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
  segment VARCHAR,
  product VARCHAR,
  rail VARCHAR,
  created_at TIMESTAMP
)
""".strip()
