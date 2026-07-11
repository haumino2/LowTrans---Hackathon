"""Seed DB from hero alerts.json + ~488 synthetic alerts; sync transactions 1:1.

Idempotent: each run replaces alerts/transactions (deterministic synthetic IDs).
Resolved cases are re-loaded; audit log is cleared.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.bedrock import embed_texts, is_configured
from agent.rag import _case_to_document
from db.models import (
    AlertRow,
    AuditRow,
    ResolvedCaseRow,
    TransactionRow,
    get_session,
    init_db,
    is_db_ready,
)
from scripts.gen_dataset import (
    alert_to_transaction_kwargs,
    build_dataset,
    summarize_dataset,
)

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def seed() -> None:
    if not is_db_ready() and not init_db():
        raise SystemExit(
            "Database not available. Default is SQLite (data/lowtrans.db); "
            "ensure USE_DB is not false. Optional: set DATABASE_URL for Postgres."
        )

    with open(DATA_DIR / "alerts.json", encoding="utf-8") as f:
        hero_alerts = json.load(f)
    with open(DATA_DIR / "resolved_cases.json", encoding="utf-8") as f:
        cases = json.load(f)

    alerts = build_dataset(hero_alerts)
    summary = summarize_dataset(alerts)

    session = get_session()
    try:
        session.query(TransactionRow).delete()
        session.query(AuditRow).delete()
        session.query(AlertRow).delete()
        session.query(ResolvedCaseRow).delete()

        for a in alerts:
            session.add(
                AlertRow(
                    id=a["id"],
                    data=a,
                    status=a.get("status", "pending"),
                )
            )

        docs = [_case_to_document(c) for c in cases]
        embeddings: list[list[float]] | None = None
        if is_configured():
            try:
                embeddings = embed_texts(docs, input_type="search_document")
            except Exception as exc:
                print(f"Warning: embed failed, storing without vectors: {exc}")

        for i, c in enumerate(cases):
            session.add(
                ResolvedCaseRow(
                    id=c["id"],
                    data=c,
                    document=docs[i],
                    embedding=embeddings[i] if embeddings else None,
                )
            )

        # Transactions stay in lockstep with the alert set (Analyst ≡ Queue)
        tx_rows = [
            TransactionRow(**alert_to_transaction_kwargs(a)) for a in alerts
        ]
        session.add_all(tx_rows)
        session.commit()

        print(
            f"Seeded {summary['total']} alerts "
            f"({summary['heroes']} heroes + {summary['total'] - summary['heroes']} synthetic), "
            f"{len(cases)} cases, {len(tx_rows)} transactions"
        )
        print(
            f"  pending={summary['pending']} clear={summary['cleared']} "
            f"review={summary['review']} escalate={summary['escalated']} "
            f"auto_clear_rate={summary['auto_clear_rate']}%"
        )
        print(
            f"  kyt: <35={summary['kyt_lt_35']} "
            f"35–65={summary['kyt_35_65']} >65={summary['kyt_gt_65']}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    seed()
