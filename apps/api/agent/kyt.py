"""Independent KYT score — on-chain exposure + Travel Rule + behavioral signals.

Does NOT reuse or echo the ML transaction score.
"""

from __future__ import annotations

from typing import Any


def _clamp(n: float, lo: float = 0.0, hi: float = 100.0) -> int:
    return int(round(max(lo, min(hi, n))))


def _travel_rule_gap_points(alert: dict[str, Any]) -> tuple[int, str]:
    status = str(alert.get("travel_rule_status") or "n/a").lower()
    if status in ("missing", "absent", "none"):
        return 25, "missing"
    if status in ("mismatch", "failed"):
        return 20, status
    if status in ("incomplete", "partial", "pending"):
        return 12, status
    return 0, status or "n/a"


def _exposure_points(exposure: dict[str, Any] | None) -> tuple[int, dict[str, Any]]:
    exp = exposure or {}
    direct = float(exp.get("direct_exposure") or 0)
    indirect = float(exp.get("indirect_exposure") or 0)
    min_hops = exp.get("min_indirect_hops")

    # Direct USD → up to 45 pts (saturates ~$50k)
    direct_pts = min(45.0, (direct / 50_000.0) * 45.0)
    # Indirect USD → up to 25 pts, slightly discounted by hop distance
    hop_factor = 1.0
    if isinstance(min_hops, int) and min_hops >= 2:
        hop_factor = max(0.45, 1.0 - 0.15 * (min_hops - 2))
    indirect_pts = min(25.0, (indirect / 40_000.0) * 25.0) * hop_factor

    pts = direct_pts + indirect_pts
    detail = {
        "direct_usd": round(direct, 2),
        "indirect_usd": round(indirect, 2),
        "min_indirect_hops": min_hops,
        "points": round(pts, 2),
    }
    return int(round(pts)), detail


def _behavioral_points(behavior: dict[str, Any] | None) -> tuple[int, str]:
    if not behavior or not behavior.get("hit"):
        return 0, "none"
    top = behavior.get("top_pattern") or {}
    sev = str(top.get("severity") or "low").lower()
    name = str(top.get("name") or "pattern")
    if sev == "high":
        return 22, name
    if sev == "medium":
        return 14, name
    return 8, name


def compute_kyt_score(
    alert: dict[str, Any],
    exposure: dict[str, Any] | None = None,
    behavior: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return KYT 0–100 from exposure, travel-rule gap, and behavioral hit."""
    exp_pts, exp_detail = _exposure_points(exposure)
    travel_pts, travel_status = _travel_rule_gap_points(alert)
    beh_pts, beh_name = _behavioral_points(behavior)

    score = _clamp(exp_pts + travel_pts + beh_pts)

    if score >= 70:
        risk_level = "high"
    elif score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    drivers: list[str] = []
    if exp_pts:
        drivers.append(
            f"on-chain exposure +{exp_pts} "
            f"(direct ${exp_detail['direct_usd']:,.0f}"
            + (
                f", indirect ${exp_detail['indirect_usd']:,.0f}"
                if exp_detail.get("indirect_usd")
                else ""
            )
            + ")"
        )
    if travel_pts:
        drivers.append(f"travel-rule {travel_status} +{travel_pts}")
    if beh_pts:
        drivers.append(f"behavioral '{beh_name}' +{beh_pts}")

    summary = (
        f"KYT {score}/100 ({risk_level})"
        + (f" · {'; '.join(drivers)}" if drivers else " · no elevated KYT drivers")
    )

    return {
        "score": score,
        "risk_level": risk_level,
        "components": {
            "exposure_points": exp_pts,
            "travel_rule_points": travel_pts,
            "behavioral_points": beh_pts,
            "exposure": exp_detail,
            "travel_rule_status": travel_status,
            "behavioral_pattern": beh_name,
        },
        "summary": summary[:320],
        "source": "kyt-v1",
    }
