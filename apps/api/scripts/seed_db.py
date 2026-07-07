"""Seed Postgres from JSON + synthetic transaction analytics data."""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta
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

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

ASSETS = ["BTC", "ETH", "USDC", "USDT", "SOL"]
PARTNERS = [
    "Summit Crypto Exchange",
    "Summit Retail Group",
    "Nordic Digital Assets",
    "Pacific On-Ramp Ltd",
]
COUNTRIES = ["United States", "Germany", "Singapore", "UAE", "Brazil"]


def seed() -> None:
    if not is_db_ready() and not init_db():
        raise SystemExit("Database not available. Run: docker compose up -d")

    with open(DATA_DIR / "alerts.json", encoding="utf-8") as f:
        alerts = json.load(f)
    with open(DATA_DIR / "resolved_cases.json", encoding="utf-8") as f:
        cases = json.load(f)

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

        # Seed transactions from alerts + synthetic history
        rng = random.Random(42)
        tx_rows: list[TransactionRow] = []
        for a in alerts:
            signals = a.get("signals", {})
            tx_rows.append(
                TransactionRow(
                    alert_id=a["id"],
                    customer_id=a["customer_id"],
                    customer_name=a["customer_name"],
                    partner=a["partner"],
                    asset=a["asset"],
                    network=a["network"],
                    direction=a["direction"],
                    amount_usd=a["amount_usd"],
                    kyt_score=a["kyt_score"],
                    risk_level=a["risk_level"],
                    travel_rule_status=a["travel_rule_status"],
                    country=a["country"],
                    rules_fired_count=len(a.get("rules_fired", [])),
                    mixer_exposure=bool(signals.get("mixer_exposure")),
                    sanctions_hit=bool(signals.get("sanctions_hit")),
                    created_at=datetime.fromisoformat(
                        a["created_at"].replace("Z", "+00:00")
                    ).replace(tzinfo=None),
                )
            )

        for i in range(120):
            kyt = rng.randint(5, 95)
            tx_rows.append(
                TransactionRow(
                    alert_id=None,
                    customer_id=f"CUST-{8000 + i}",
                    customer_name=f"Synthetic User {i}",
                    partner=rng.choice(PARTNERS),
                    asset=rng.choice(ASSETS),
                    network=rng.choice(["Ethereum", "Bitcoin", "Solana", "Tron"]),
                    direction=rng.choice(["deposit", "withdrawal"]),
                    amount_usd=round(rng.uniform(100, 85000), 2),
                    kyt_score=kyt,
                    risk_level="high" if kyt > 65 else "medium" if kyt > 40 else "low",
                    travel_rule_status=rng.choice(
                        ["complete", "missing", "incomplete", "mismatch"]
                    ),
                    country=rng.choice(COUNTRIES),
                    rules_fired_count=rng.randint(0, 4),
                    mixer_exposure=kyt > 70 and rng.random() > 0.5,
                    sanctions_hit=kyt > 80 and rng.random() > 0.85,
                    created_at=datetime.utcnow() - timedelta(days=rng.randint(0, 30)),
                )
            )

        session.add_all(tx_rows)
        session.commit()
        print(f"Seeded {len(alerts)} alerts, {len(cases)} cases, {len(tx_rows)} transactions")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
