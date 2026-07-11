"""Fiat–crypto bridge tracer — input-varying mock correlation of bank drop ↔ wallet funding.

Simulated, but the rails, intermediary hops, latency and match confidence vary by
network, asset, amount and country so each case reads differently.
"""

from __future__ import annotations

from typing import Any

# On-chain rail label per network.
_CRYPTO_RAIL = {
    "ethereum": "ERC-20 transfer",
    "bitcoin": "BTC UTXO settlement",
    "tron": "TRC-20 transfer",
    "solana": "SPL token transfer",
}

# Fiat rail per (rough) country grouping.
_EU = {"poland", "estonia", "germany", "france", "spain", "netherlands", "sweden"}


def _fiat_rail(country: str) -> str:
    c = (country or "").lower()
    if c in _EU:
        return "SEPA credit transfer"
    if "united states" in c or c in ("us", "usa"):
        return "ACH / FedWire"
    if "emirates" in c or "uae" in c:
        return "UAEFTS wire"
    return "SWIFT wire"


def trace_bridge(alert: dict[str, Any]) -> dict[str, Any]:
    direction = str(alert.get("direction") or "withdrawal").lower()
    partner = alert.get("partner") or "Unknown partner"
    amount = float(alert.get("amount_usd") or 0)
    asset = alert.get("asset") or "USDC"
    network = str(alert.get("network") or "Ethereum")
    country = alert.get("country") or "US"
    travel = str(alert.get("travel_rule_status") or "complete").lower()
    signals = alert.get("signals") or {}
    mixer = bool(signals.get("mixer_exposure")) or "mixer_exposure" in (alert.get("risk_tags") or [])
    wallet = str(alert.get("wallet_address") or "")[:14] + "…"

    crypto_rail = _CRYPTO_RAIL.get(network.lower(), f"{network} transfer")
    fiat_rail = _fiat_rail(str(country))

    # Latency grows with amount and mixer obfuscation.
    gap_hours = 2
    if amount >= 25000:
        gap_hours = 6
    if amount >= 50000:
        gap_hours = 12
    if mixer:
        gap_hours += 8

    crypto_leg = {
        "leg": None,
        "rail": "crypto",
        "detail": f"{crypto_rail} {asset} on {network} · {wallet}",
        "amount_usd": amount,
    }
    fiat_leg = {
        "leg": None,
        "rail": "fiat",
        "detail": f"{fiat_rail} via {partner} ({country})",
        "amount_usd": amount,
    }

    if direction == "deposit":
        legs = [dict(fiat_leg, leg=1), dict(crypto_leg, leg=2)]
        narrative = f"Fiat inbound ({fiat_rail}) at {partner} correlated to on-chain {asset} credit"
    else:
        legs = [dict(crypto_leg, leg=1), dict(fiat_leg, leg=2)]
        narrative = f"On-chain {asset} debit correlated to fiat payout ({fiat_rail}) at {partner}"

    # Insert an obfuscation hop when mixer exposure or very large amount.
    if mixer or amount >= 50000:
        hop = {
            "leg": 99,
            "rail": "crypto",
            "detail": "Intermediary hop — bridge / mixer obscures 1:1 correlation",
            "amount_usd": round(amount * 0.6, 2),
        }
        legs.insert(1, hop)

    # Confidence in the fiat↔crypto match degrades with obfuscation / missing data.
    if mixer:
        matched, confidence, note = False, 0.42, "Partial — mixer hop breaks direct linkage"
    elif travel in ("missing", "incomplete"):
        matched, confidence, note = True, 0.71, "Correlated, but Travel Rule payload incomplete"
    else:
        matched, confidence, note = True, 0.9, "Strong 1:1 fiat↔crypto correlation"

    return {
        "partner": partner,
        "direction": direction,
        "legs": legs,
        "latency_hours_est": gap_hours,
        "matched": matched,
        "match_confidence": confidence,
        "summary": f"{narrative} (Δ≈{gap_hours}h · {note})",
        "source": "mock:fiat-crypto-bridge-v3",
    }
