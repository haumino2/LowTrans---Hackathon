"""Demo scenario presets — deterministic transactions that drive real agent output.

Each scenario ships a full submit payload (identity + signals). Crypto scenarios
also have an on-chain graph template written by ingest.py so the
OnChain_Graph_Analyzer and Connections Graph tab light up. Retail scenarios
return no graph (rail=retail / Fiat) — triage still runs without on-chain data.

Decisions are anchored by deterministic policy gates + the explainable ML scorer:
  Crypto:
  - clean_cex            -> CLEAR    (low amount, travel complete, aged wallet)
  - mixer_hop            -> ESCALATE (mixer + Travel Rule missing on high-value)
  - sanctions            -> ESCALATE (OFAC hard gate)
  - structuring          -> REVIEW   (smurfing band, no hard gate)
  Retail:
  - salary_inflow        -> CLEAR    (payroll deposit)
  - ewallet_topup        -> CLEAR    (small top-up)
  - remittance_highvalue -> REVIEW   (cross-border corridor, sub-threshold)
  - merchant_payout      -> CLEAR    (SME payout)
"""

from __future__ import annotations

from typing import Any

RETAIL_SCENARIO_IDS = frozenset(
    {"salary_inflow", "ewallet_topup", "remittance_highvalue", "merchant_payout"}
)


def _short(addr: str) -> str:
    addr = str(addr or "")
    if len(addr) > 12:
        return f"{addr[:6]}...{addr[-4:]}"
    return addr or "wallet"


# --- Scenario payloads (what the submit form pre-fills) -----------------------

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "clean_cex",
        "label": "Clean CEX withdrawal",
        "description": "Low-value, Travel-Rule-complete withdrawal to a known exchange from an aged wallet.",
        "expected_decision": "CLEAR",
        "payload": {
            "customer_name": "Daniel Foster",
            "customer_id": "CUST-7781",
            "amount_usd": 2400,
            "asset": "USDC",
            "network": "Ethereum",
            "direction": "withdrawal",
            "counterparty": "Coinbase Hot Wallet",
            "partner": "Nordic Digital Assets",
            "travel_rule_status": "complete",
            "country": "United States",
            "wallet_address": "0x7a3f2b9e4c1d8f6a2e5b9c2d",
            "account_age_days": 420,
            "connections": 3,
            "device_risk": "low",
            "mixer_exposure": False,
            "sanctions_hit": False,
            "pep_hit": False,
            "risk_tags": [],
            "segment": "vasp",
            "product": "crypto",
            "rail": "crypto",
        },
    },
    {
        "id": "mixer_hop",
        "label": "Mixer-adjacent high-value",
        "description": "Large ETH withdrawal with Tornado-Cash exposure and missing Travel Rule from a 3-day-old wallet.",
        "expected_decision": "ESCALATE",
        "payload": {
            "customer_name": "Viktor Petrov",
            "customer_id": "CUST-2290",
            "amount_usd": 52000,
            "asset": "ETH",
            "network": "Ethereum",
            "direction": "withdrawal",
            "counterparty": "Tornado Cash adjacent cluster",
            "partner": "Summit Crypto Exchange",
            "travel_rule_status": "missing",
            "country": "Estonia",
            "wallet_address": "0x8b2e4f1a9c7d3e5b8a1f4d2c",
            "account_age_days": 3,
            "connections": 12,
            "device_risk": "high",
            "mixer_exposure": True,
            "sanctions_hit": False,
            "pep_hit": False,
            "risk_tags": ["mixer_exposure", "high_risk_jurisdiction"],
            "segment": "vasp",
            "product": "crypto",
            "rail": "crypto",
        },
    },
    {
        "id": "sanctions",
        "label": "Sanctioned counterparty (OFAC)",
        "description": "BTC transfer to an OFAC-SDN-adjacent counterparty with PEP proximity.",
        "expected_decision": "ESCALATE",
        "payload": {
            "customer_name": "Omar Nassar",
            "customer_id": "CUST-9902",
            "amount_usd": 4200,
            "asset": "BTC",
            "network": "Bitcoin",
            "direction": "withdrawal",
            "counterparty": "OFAC SDN Adjacent",
            "partner": "Summit Retail Group",
            "travel_rule_status": "complete",
            "country": "United Arab Emirates",
            "wallet_address": "1A1zP1eP5QGefi2DMPTfTL5",
            "account_age_days": 14,
            "connections": 9,
            "device_risk": "medium",
            "mixer_exposure": False,
            "sanctions_hit": True,
            "pep_hit": True,
            "risk_tags": ["sanctions_proximity"],
            "segment": "vasp",
            "product": "crypto",
            "rail": "crypto",
        },
    },
    {
        "id": "structuring",
        "label": "Structuring / smurfing",
        "description": "Sub-$10k withdrawal fanned out to several new wallets — classic CTR-evasion band.",
        "expected_decision": "REVIEW",
        "payload": {
            "customer_name": "Lena Novak",
            "customer_id": "CUST-6650",
            "amount_usd": 9500,
            "asset": "USDT",
            "network": "Tron",
            "direction": "withdrawal",
            "counterparty": "Multiple new wallets",
            "partner": "Pacific On-Ramp Ltd",
            "travel_rule_status": "incomplete",
            "country": "Poland",
            "wallet_address": "TRX9aBcD3eFgH5jKmN7pQrS",
            "account_age_days": 25,
            "connections": 12,
            "device_risk": "medium",
            "mixer_exposure": False,
            "sanctions_hit": False,
            "pep_hit": False,
            "risk_tags": ["structuring", "high_risk_jurisdiction"],
            "segment": "vasp",
            "product": "crypto",
            "rail": "crypto",
        },
    },
    {
        "id": "salary_inflow",
        "label": "Payroll salary deposit",
        "description": "Routine payroll credit (~$1,850) to a retail customer — no on-chain wallet.",
        "expected_decision": "CLEAR",
        "payload": {
            "customer_name": "Mai Nguyen",
            "customer_id": "CUST-R401",
            "amount_usd": 1850,
            "asset": "VND",
            "network": "Fiat",
            "direction": "deposit",
            "counterparty": "Acme Corp Payroll",
            "partner": "LowTrans Retail Bank",
            "travel_rule_status": "complete",
            "country": "Vietnam",
            "account_age_days": 640,
            "connections": 2,
            "device_risk": "low",
            "mixer_exposure": False,
            "sanctions_hit": False,
            "pep_hit": False,
            "risk_tags": [],
            "segment": "retail",
            "product": "payroll",
            "rail": "retail",
            "kyc_tier": "full",
            "kyc_verification_level": "id + liveness",
            "product_mix": ["payroll", "ewallet"],
            "prior_alerts": {"count": 0, "latest_disposition": None},
        },
    },
    {
        "id": "ewallet_topup",
        "label": "E-wallet top-up",
        "description": "Small retail e-wallet top-up — low value, aged account, no risk flags.",
        "expected_decision": "CLEAR",
        "payload": {
            "customer_name": "James Okonkwo",
            "customer_id": "CUST-R512",
            "amount_usd": 45,
            "asset": "USD",
            "network": "Fiat",
            "direction": "deposit",
            "counterparty": "Self top-up · debit card",
            "partner": "LowTrans Wallet",
            "travel_rule_status": "complete",
            "country": "United States",
            "account_age_days": 280,
            "connections": 1,
            "device_risk": "low",
            "mixer_exposure": False,
            "sanctions_hit": False,
            "pep_hit": False,
            "risk_tags": [],
            "segment": "retail",
            "product": "ewallet",
            "rail": "retail",
            "kyc_tier": "basic",
            "kyc_verification_level": "phone + id",
            "product_mix": ["ewallet"],
            "prior_alerts": {"count": 0, "latest_disposition": None},
        },
    },
    {
        "id": "remittance_highvalue",
        "label": "Cross-border remittance (corridor)",
        "description": "Sub-threshold cross-border remittance (~$7,400) on a higher-risk corridor — analyst review.",
        "expected_decision": "REVIEW",
        "payload": {
            "customer_name": "Aisha Rahman",
            "customer_id": "CUST-R628",
            "amount_usd": 7400,
            "asset": "USD",
            "network": "Fiat",
            "direction": "withdrawal",
            "counterparty": "Family remittance · PH corridor",
            "partner": "LowTrans Remit",
            "travel_rule_status": "incomplete",
            "country": "Philippines",
            "account_age_days": 5,
            "connections": 16,
            "device_risk": "high",
            "mixer_exposure": False,
            "sanctions_hit": False,
            "pep_hit": False,
            "risk_tags": ["high_risk_jurisdiction", "corridor_risk"],
            "segment": "retail",
            "product": "remittance",
            "rail": "retail",
            "kyc_tier": "enhanced",
            "kyc_verification_level": "id + sof",
            "product_mix": ["remittance", "ewallet"],
            "prior_alerts": {
                "count": 2,
                "latest_disposition": "REVIEW",
                "latest_alert_id": "ALT-PRIOR-R628",
            },
        },
    },
    {
        "id": "merchant_payout",
        "label": "SME merchant payout",
        "description": "Routine SME settlement payout — aged merchant, complete KYC, no flags.",
        "expected_decision": "CLEAR",
        "payload": {
            "customer_name": "Saigon Cafe Co.",
            "customer_id": "CUST-S902",
            "amount_usd": 3200,
            "asset": "VND",
            "network": "Fiat",
            "direction": "withdrawal",
            "counterparty": "Merchant settlement account",
            "partner": "LowTrans Merchant Acquiring",
            "travel_rule_status": "complete",
            "country": "Vietnam",
            "account_age_days": 510,
            "connections": 4,
            "device_risk": "low",
            "mixer_exposure": False,
            "sanctions_hit": False,
            "pep_hit": False,
            "risk_tags": [],
            "segment": "sme",
            "product": "merchant",
            "rail": "retail",
            "kyc_tier": "full",
            "kyc_verification_level": "kyb + ubo",
            "product_mix": ["merchant"],
            "prior_alerts": {"count": 1, "latest_disposition": "CLEAR"},
        },
    },
]

_BY_ID = {s["id"]: s for s in SCENARIOS}


def get_scenarios() -> list[dict[str, Any]]:
    """Public scenario list for the submit form."""
    return [
        {
            "id": s["id"],
            "label": s["label"],
            "description": s["description"],
            "expected_decision": s["expected_decision"],
            "payload": s["payload"],
        }
        for s in SCENARIOS
    ]


def get_scenario(scenario_id: str) -> dict[str, Any] | None:
    return _BY_ID.get(scenario_id)


# --- Graph templates ----------------------------------------------------------


def build_scenario_graph(scenario_id: str, alert: dict[str, Any]) -> dict[str, Any] | None:
    """Construct an on-chain graph for a submitted scenario, keyed to the real
    identity in the alert so the wallet shown matches what the user submitted.

    Retail / Fiat scenarios have no on-chain graph — returns None (ingest skips write).
    """
    if scenario_id not in _BY_ID:
        return None
    if scenario_id in RETAIL_SCENARIO_IDS:
        return None
    payload = (_BY_ID[scenario_id].get("payload") or {})
    if str(payload.get("rail") or "").lower() == "retail":
        return None

    aid = str(alert.get("id", ""))
    name = str(alert.get("customer_name", "Customer"))
    cid = str(alert.get("customer_id", ""))
    country = str(alert.get("country", ""))
    wallet = _short(alert.get("wallet_address", ""))
    amount = float(alert.get("amount_usd") or 0)
    cust_sub = f"{cid} · {country}".strip(" ·")

    customer = {
        "id": "customer-main",
        "type": "customer",
        "label": name,
        "subtitle": cust_sub or cid,
        "position": {"x": 400, "y": 50},
    }
    primary_wallet = {
        "id": "wallet-main",
        "type": "wallet",
        "label": wallet,
        "subtitle": f"Primary wallet · {alert.get('account_age_days', '?')} days",
        "position": {"x": 400, "y": 200},
    }
    owns_edge = {"id": "e-owns", "source": "customer-main", "target": "wallet-main", "label": "Owns", "amount_usd": None}

    if scenario_id == "clean_cex":
        customer["risk"] = "low"
        primary_wallet["risk"] = "low"
        nodes = [
            customer,
            primary_wallet,
            {"id": "cex-coinbase", "type": "counterparty", "label": "Coinbase Hot Wallet", "subtitle": "Known CEX", "risk": "low", "position": {"x": 250, "y": 360}},
            {"id": "cex-kraken", "type": "counterparty", "label": "Kraken Deposit", "subtitle": "Known CEX", "risk": "low", "position": {"x": 550, "y": 360}},
        ]
        edges = [
            owns_edge,
            {"id": "e2", "source": "wallet-main", "target": "cex-coinbase", "label": f"${amount:,.0f} withdrawal", "amount_usd": amount},
            {"id": "e3", "source": "cex-kraken", "target": "wallet-main", "label": "$1,900 prior deposit", "amount_usd": 1900},
        ]
        flagged: list[str] = []

    elif scenario_id == "mixer_hop":
        customer["risk"] = "high"
        primary_wallet["risk"] = "high"
        nodes = [
            customer,
            primary_wallet,
            {"id": "cex-coinbase", "type": "counterparty", "label": "Coinbase Hot Wallet", "subtitle": "Known CEX", "risk": "low", "position": {"x": 150, "y": 350}},
            {"id": "mixer-tornado", "type": "mixer", "label": "Tornado Cash Pool", "subtitle": "Mixer · OFAC sanctioned", "risk": "high", "position": {"x": 400, "y": 350}},
            {"id": "cluster-tc-adjacent", "type": "counterparty", "label": "TC Adjacent Cluster", "subtitle": "2-hop mixer exposure", "risk": "high", "position": {"x": 650, "y": 350}},
            {"id": "wallet-mule-1", "type": "wallet", "label": "0x3f1a...9c2d", "subtitle": "Mule wallet · 12 connections", "risk": "medium", "position": {"x": 650, "y": 500}},
            {"id": "vasp-unknown", "type": "counterparty", "label": "Unknown VASP", "subtitle": "Travel Rule missing", "risk": "medium", "position": {"x": 150, "y": 500}},
        ]
        edges = [
            owns_edge,
            {"id": "e2", "source": "wallet-main", "target": "cex-coinbase", "label": "$8,200 deposit", "amount_usd": 8200},
            {"id": "e3", "source": "wallet-main", "target": "mixer-tornado", "label": "$18,400 via bridge", "amount_usd": 18400},
            {"id": "e4", "source": "mixer-tornado", "target": "cluster-tc-adjacent", "label": "2-hop exposure", "amount_usd": 15200},
            {"id": "e5", "source": "cluster-tc-adjacent", "target": "wallet-mule-1", "label": "$9,600 transfer", "amount_usd": 9600},
            {"id": "e6", "source": "wallet-main", "target": "vasp-unknown", "label": f"${amount:,.0f} withdrawal", "amount_usd": amount},
        ]
        flagged = ["wallet-main", "mixer-tornado", "cluster-tc-adjacent"]

    elif scenario_id == "sanctions":
        customer["risk"] = "high"
        primary_wallet["risk"] = "high"
        nodes = [
            customer,
            primary_wallet,
            {"id": "sdn-adjacent", "type": "counterparty", "label": "OFAC SDN Adjacent", "subtitle": "87% fuzzy match", "risk": "high", "position": {"x": 200, "y": 380}},
            {"id": "pep-entity", "type": "counterparty", "label": "PEP Adjacent Entity", "subtitle": "Government-linked", "risk": "high", "position": {"x": 600, "y": 380}},
            {"id": "exchange-kraken", "type": "counterparty", "label": "Kraken Deposit", "subtitle": "Known CEX", "risk": "low", "position": {"x": 100, "y": 520}},
            {"id": "wallet-intermediary", "type": "wallet", "label": "bc1q...7hguz", "subtitle": "Intermediary · 2 hops", "risk": "medium", "position": {"x": 400, "y": 520}},
        ]
        edges = [
            owns_edge,
            {"id": "e2", "source": "wallet-main", "target": "sdn-adjacent", "label": f"${amount:,.0f} transfer", "amount_usd": amount},
            {"id": "e3", "source": "wallet-main", "target": "pep-entity", "label": "$2,800 transfer", "amount_usd": 2800},
            {"id": "e4", "source": "exchange-kraken", "target": "wallet-main", "label": "$12,000 deposit", "amount_usd": 12000},
            {"id": "e5", "source": "wallet-main", "target": "wallet-intermediary", "label": "$8,500 withdrawal", "amount_usd": 8500},
            {"id": "e6", "source": "wallet-intermediary", "target": "sdn-adjacent", "label": "Indirect link", "amount_usd": 3100},
        ]
        flagged = ["wallet-main", "sdn-adjacent", "pep-entity"]

    else:  # structuring
        customer["risk"] = "medium"
        primary_wallet["risk"] = "medium"
        nodes = [
            customer,
            primary_wallet,
            {"id": "cex-source", "type": "counterparty", "label": "On-Ramp Deposit", "subtitle": "Known CEX", "risk": "low", "position": {"x": 700, "y": 200}},
            {"id": "wallet-struct-1", "type": "wallet", "label": "0xabc1...def2", "subtitle": "New wallet · 2 days", "risk": "medium", "position": {"x": 200, "y": 400}},
            {"id": "wallet-struct-2", "type": "wallet", "label": "0x1234...5678", "subtitle": "New wallet · 1 day", "risk": "medium", "position": {"x": 400, "y": 400}},
            {"id": "wallet-struct-3", "type": "wallet", "label": "0x9abc...0def", "subtitle": "New wallet · 3 days", "risk": "medium", "position": {"x": 600, "y": 400}},
        ]
        edges = [
            owns_edge,
            {"id": "e2", "source": "cex-source", "target": "wallet-main", "label": "$28,500 deposit", "amount_usd": 28500},
            {"id": "e3", "source": "wallet-main", "target": "wallet-struct-1", "label": "$9,500", "amount_usd": 9500},
            {"id": "e4", "source": "wallet-main", "target": "wallet-struct-2", "label": "$9,200", "amount_usd": 9200},
            {"id": "e5", "source": "wallet-main", "target": "wallet-struct-3", "label": "$8,900", "amount_usd": 8900},
        ]
        flagged = ["wallet-main", "wallet-struct-1", "wallet-struct-2", "wallet-struct-3"]

    return {
        "alert_id": aid,
        "customer_name": name,
        "flagged_node_ids": flagged,
        "nodes": nodes,
        "edges": edges,
    }
