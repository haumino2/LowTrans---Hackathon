"""Generate synthetic alert history for a realistic ~500-alert queue.

Hero alerts (from alerts.json) stay untouched aside from demo_hero + fresh timestamps.
Synthetic IDs are deterministic (ALT-4001+) so re-seeding is idempotent.
"""

from __future__ import annotations

import hashlib
import random
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any

SYNTHETIC_COUNT = 488
SYNTHETIC_START = 4001

ASSETS_NETWORKS = [
    ("BTC", "Bitcoin"),
    ("ETH", "Ethereum"),
    ("USDC", "Ethereum"),
    ("USDT", "Tron"),
    ("USDT", "Ethereum"),
    ("SOL", "Solana"),
    ("USDC", "Solana"),
]

PARTNERS = [
    ("Summit Crypto Exchange", "185654"),
    ("Summit Retail Group, Inc.", "185654"),
    ("Nordic Digital Assets", "220101"),
    ("Pacific On-Ramp Ltd", "330202"),
    ("LatAm Rails Partners", "440303"),
]

COUNTRIES = [
    ("United States", "CA", "US"),
    ("United States", "NY", "US"),
    ("United States", "TX", "US"),
    ("Germany", "Berlin", "DE"),
    ("Singapore", "Central", "SG"),
    ("UAE", "Dubai", "AE"),
    ("Brazil", "SP", "BR"),
    ("United Kingdom", "London", "GB"),
    ("Japan", "Tokyo", "JP"),
    ("Canada", "ON", "CA"),
    ("Spain", "Madrid", "ES"),
    ("Australia", "NSW", "AU"),
]

FIRST_NAMES = [
    "Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey", "Riley", "Quinn",
    "Avery", "Cameron", "Drew", "Jamie", "Kai", "Noah", "Mia", "Liam",
    "Sofia", "Lucas", "Emma", "Olivia", "Ethan", "Ava", "Harper", "Leo",
    "Amelia", "Mason", "Isabella", "Elijah", "Charlotte", "Henry",
]
LAST_NAMES = [
    "Nguyen", "Patel", "Kim", "Silva", "Andersen", "Rossi", "Murphy",
    "Schmidt", "Costa", "Ivanov", "Berg", "Fischer", "Santos", "Lee",
    "Garcia", "Brown", "Wilson", "Martinez", "Lopez", "Gonzalez",
]

DEVICE_OS = ["iOS 17", "iOS 18", "Android 14", "Windows 11", "macOS 14", "macOS 15"]
COUNTERPARTIES = [
    "Binance hot wallet",
    "Coinbase deposit",
    "Kraken withdrawal",
    "Self-custody wallet",
    "OTC desk desk-A",
    "Exchange cluster unknown",
    "Bridge hop destination",
    "Retail P2P counterparty",
]

RULE_CATALOG = [
    {"id": "R-101", "name": "Mixer Exposure Detected", "severity": "critical"},
    {"id": "R-001", "name": "Sanctions List Fuzzy Match", "severity": "critical"},
    {"id": "R-205", "name": "Travel Rule Missing > $3K", "severity": "high"},
    {"id": "R-088", "name": "New Account High Value Withdrawal", "severity": "medium"},
    {"id": "R-042", "name": "PEP Adjacent Connection", "severity": "high"},
    {"id": "R-150", "name": "Rapid Movement Pattern", "severity": "medium"},
    {"id": "R-180", "name": "High-Risk Jurisdiction", "severity": "medium"},
    {"id": "R-220", "name": "Structuring Suspected", "severity": "high"},
]


def _wallet(rng: random.Random, network: str) -> str:
    raw = hashlib.sha256(f"{rng.random()}-{rng.randint(0, 10**9)}".encode()).hexdigest()
    if network == "Bitcoin":
        return "bc1q" + raw[:38]
    if network == "Solana":
        return raw[:44]
    return "0x" + raw[:40]


def _sample_kyt(rng: random.Random) -> int:
    r = rng.random()
    if r < 0.70:
        return rng.randint(1, 34)
    if r < 0.90:
        return rng.randint(35, 65)
    return rng.randint(66, 98)


def _assign_statuses(count: int, rng: random.Random) -> list[str]:
    """Exact status mix so pending heroes + synth ≈ 12–15 total."""
    # 488: ~88% clear, ~7% review, ~4% escalate, ~1% pending (≤3 synth pending)
    n_pending = min(3, max(1, round(count * 0.006)))
    n_escalate = round(count * 0.04)
    n_review = round(count * 0.07)
    n_clear = count - n_pending - n_escalate - n_review
    statuses = (
        ["clear"] * n_clear
        + ["review"] * n_review
        + ["escalate"] * n_escalate
        + ["pending"] * n_pending
    )
    rng.shuffle(statuses)
    return statuses


def _weighted_created_at(rng: random.Random, now: datetime) -> datetime:
    """Spread across last 90 days with heavier weight on recent days."""
    # u^2 skews toward 0 → recent
    day_offset = int((rng.random() ** 1.7) * 90)
    hour = rng.randint(0, 23)
    minute = rng.randint(0, 59)
    return (now - timedelta(days=day_offset, hours=hour % 12, minutes=minute)).replace(
        microsecond=0
    )


def _risk_level(kyt: int) -> str:
    if kyt > 65:
        return "high"
    if kyt > 40:
        return "medium"
    return "low"


def _travel_rule(rng: random.Random, amount: float, kyt: int) -> str:
    if amount < 3000:
        return rng.choice(["n/a", "complete", "complete", "complete"])
    if kyt > 65 and rng.random() < 0.45:
        return rng.choice(["missing", "incomplete", "mismatch"])
    return rng.choices(
        ["complete", "incomplete", "missing", "mismatch"],
        weights=[70, 15, 10, 5],
    )[0]


def _build_rules(
    rng: random.Random,
    *,
    mixer: bool,
    sanctions: bool,
    travel: str,
    amount: float,
    account_age: int,
    kyt: int,
) -> tuple[list[dict[str, str]], list[str]]:
    rules: list[dict[str, str]] = []
    tags: list[str] = []
    if mixer:
        rules.append(RULE_CATALOG[0])
        tags.append("mixer_exposure")
    if sanctions:
        rules.append(RULE_CATALOG[1])
        tags.append("sanctions_near_match")
    if travel in ("missing", "incomplete") and amount >= 3000:
        rules.append(RULE_CATALOG[2])
        tags.append("travel_rule_missing")
    if account_age < 14 and amount >= 5000 and kyt > 40:
        rules.append(RULE_CATALOG[3])
        tags.append("new_wallet")
    if kyt > 50 and rng.random() < 0.25:
        extra = rng.choice(RULE_CATALOG[4:])
        if extra not in rules:
            rules.append(extra)
            tags.append(extra["name"].lower().replace(" ", "_")[:28])
    if kyt < 35:
        rules = []
        tags = []
    return rules, tags


def generate_synthetic_alert(
    index: int,
    rng: random.Random,
    now: datetime,
    status: str,
) -> dict[str, Any]:
    """Build one synthetic alert. index is 0-based."""
    alert_id = f"ALT-{SYNTHETIC_START + index}"
    kyt = _sample_kyt(rng)
    asset, network = rng.choice(ASSETS_NETWORKS)
    partner, partner_id = rng.choice(PARTNERS)
    country, state, ip_cc = rng.choice(COUNTRIES)
    first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
    name = f"{first} {last}"
    direction = rng.choice(["deposit", "withdrawal", "withdrawal", "deposit"])
    # Amount skewed: mostly retail, thin high tail
    amount = round(10 ** rng.uniform(2.0, 4.85), 2)  # ~$100–$70k
    if kyt > 65:
        amount = max(amount, round(rng.uniform(8000, 95000), 2))

    mixer = kyt > 65 and rng.random() < 0.32
    sanctions = kyt > 75 and rng.random() < 0.12
    pep = kyt > 70 and rng.random() < 0.08
    account_age = rng.randint(0, 900)
    if kyt > 65 and rng.random() < 0.4:
        account_age = rng.randint(0, 21)

    travel = _travel_rule(rng, amount, kyt)
    rules, tags = _build_rules(
        rng,
        mixer=mixer,
        sanctions=sanctions,
        travel=travel,
        amount=amount,
        account_age=account_age,
        kyt=kyt,
    )
    created = _weighted_created_at(rng, now)
    cust_n = 10000 + index
    flow = "Withdrawal Flow" if direction == "withdrawal" else "Deposit Flow"
    if account_age < 3:
        flow = "Registration Flow"

    sanctions_status = "clear"
    matches = 0
    note = None
    if sanctions:
        sanctions_status = "hit"
        matches = rng.randint(1, 2)
        note = "OFAC SDN fuzzy match"
    elif kyt > 60 and rng.random() < 0.15:
        sanctions_status = "review"
        matches = 1
        note = "Fuzzy name match - under review"

    prior_count = rng.randint(0, 3)

    return {
        "id": alert_id,
        "customer_id": f"CUST-{cust_n}",
        "customer_name": name,
        "email": f"{first.lower()}.{last.lower()}{index % 97}@mail.com",
        "partner": partner,
        "partner_id": partner_id,
        "session_id": f"SES-{hashlib.md5(alert_id.encode()).hexdigest()[:8]}",
        "status": status,
        "asset": asset,
        "network": network,
        "amount_usd": amount,
        "direction": direction,
        "kyt_score": kyt,
        "risk_level": _risk_level(kyt),
        "risk_tags": tags,
        "wallet_address": _wallet(rng, network),
        "counterparty": rng.choice(COUNTERPARTIES),
        "travel_rule_status": travel,
        "account_age_days": account_age,
        "device_os": rng.choice(DEVICE_OS),
        "flow_type": flow,
        "country": country,
        "state": state,
        "address": f"{rng.randint(1, 9999)} Sample Ave",
        "zip": f"{rng.randint(10000, 99999)}",
        "phone": f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}",
        "connections": rng.randint(0, 18),
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "signals": {
            "wallet_age_days": account_age,
            "mixer_exposure": mixer,
            "sanctions_hit": sanctions,
            "pep_hit": pep,
            "device_risk": "high" if kyt > 65 else "medium" if kyt > 40 else "low",
            "ip_country": ip_cc,
        },
        "rules_fired": rules,
        "sanctions_screening": {
            "status": sanctions_status,
            "matches": matches,
            **({"note": note} if note else {}),
        },
        "crypto_details": {
            "chain": network,
            "confirmations": rng.randint(1, 24),
        },
        "segment": "vasp",
        "product": "crypto",
        "rail": "crypto",
        "kyc_tier": "vasp",
        "kyc_verification_level": "travel-rule + kyt",
        "onboarding_date": (now - timedelta(days=account_age)).date().isoformat(),
        "product_mix": ["crypto"],
        "prior_alerts": {
            "count": prior_count,
            "latest_disposition": (
                rng.choice(["CLEAR", "REVIEW", "ESCALATE"]) if prior_count else None
            ),
            "latest_alert_id": None,
            "latest_at": None,
        },
        "demo_hero": False,
    }


def prepare_hero_alerts(
    heroes: list[dict[str, Any]],
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Clone hero alerts, mark demo_hero, keep pending, refresh created_at for demo."""
    now = now or datetime.utcnow()
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(heroes):
        a = deepcopy(raw)
        a["demo_hero"] = True
        a["status"] = "pending"
        # Drop runtime fields so a fresh seed starts clean for heroes
        for key in (
            "triage_result",
            "override",
            "supervisor_approval",
            "assigned_to",
            "notes",
            "case_id",
            "case_state",
            "case_assigned_to",
            "case_notes",
        ):
            a.pop(key, None)
        # Stagger heroes across the last ~18 hours so they look live
        ts = now - timedelta(hours=i, minutes=(i * 7) % 60)
        a["created_at"] = ts.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        # Crypto defaults for legacy hero alerts missing retail/crypto metadata
        a.setdefault("rail", "crypto")
        a.setdefault("segment", "vasp")
        a.setdefault("product", "crypto")
        a.setdefault("kyc_tier", "vasp")
        a.setdefault("kyc_verification_level", "travel-rule + kyt")
        age = int(a.get("account_age_days") or 30)
        a.setdefault(
            "onboarding_date",
            (now - timedelta(days=age)).date().isoformat(),
        )
        a.setdefault("product_mix", ["crypto"])
        a.setdefault(
            "prior_alerts",
            {
                "count": 1 if int(a.get("kyt_score") or 0) >= 40 else 0,
                "latest_disposition": "REVIEW" if int(a.get("kyt_score") or 0) >= 40 else None,
                "latest_alert_id": None,
                "latest_at": None,
            },
        )
        out.append(a)
    return out


def build_dataset(
    hero_alerts: list[dict[str, Any]],
    *,
    synthetic_count: int = SYNTHETIC_COUNT,
    seed: int = 42,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Return hero + synthetic alerts (~500). Deterministic given seed."""
    now = now or datetime.utcnow()
    heroes = prepare_hero_alerts(hero_alerts, now=now)
    rng = random.Random(seed)
    statuses = _assign_statuses(synthetic_count, rng)
    synthetic = [
        generate_synthetic_alert(i, rng, now, statuses[i])
        for i in range(synthetic_count)
    ]
    return heroes + synthetic


def alert_to_transaction_kwargs(a: dict[str, Any]) -> dict[str, Any]:
    """Map alert JSON → TransactionRow constructor kwargs (minus ORM extras)."""
    signals = a.get("signals") or {}
    created_raw = a.get("created_at") or ""
    if isinstance(created_raw, str):
        created = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).replace(
            tzinfo=None
        )
    else:
        created = datetime.utcnow()
    return {
        "alert_id": a["id"],
        "customer_id": a.get("customer_id") or "",
        "customer_name": a.get("customer_name") or "",
        "partner": a.get("partner") or "",
        "asset": a.get("asset") or "",
        "network": a.get("network") or "",
        "direction": a.get("direction") or "",
        "amount_usd": float(a.get("amount_usd") or 0),
        "kyt_score": int(a.get("kyt_score") or 0),
        "risk_level": a.get("risk_level") or "",
        "travel_rule_status": a.get("travel_rule_status") or "",
        "country": a.get("country") or "",
        "rules_fired_count": len(a.get("rules_fired") or []),
        "mixer_exposure": bool(signals.get("mixer_exposure")),
        "sanctions_hit": bool(signals.get("sanctions_hit")),
        "segment": a.get("segment"),
        "product": a.get("product"),
        "rail": a.get("rail"),
        "created_at": created,
    }


def summarize_dataset(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    heroes = sum(1 for a in alerts if a.get("demo_hero"))
    pending = sum(1 for a in alerts if a.get("status") == "pending")
    cleared = sum(1 for a in alerts if a.get("status") == "clear")
    review = sum(1 for a in alerts if a.get("status") == "review")
    escalated = sum(1 for a in alerts if a.get("status") == "escalate")
    triaged = cleared + review + escalated
    return {
        "total": len(alerts),
        "heroes": heroes,
        "pending": pending,
        "cleared": cleared,
        "review": review,
        "escalated": escalated,
        "auto_clear_rate": round(cleared / triaged * 100, 1) if triaged else 0.0,
        "kyt_lt_35": sum(1 for a in alerts if int(a.get("kyt_score") or 0) < 35),
        "kyt_35_65": sum(
            1 for a in alerts if 35 <= int(a.get("kyt_score") or 0) <= 65
        ),
        "kyt_gt_65": sum(1 for a in alerts if int(a.get("kyt_score") or 0) > 65),
    }
