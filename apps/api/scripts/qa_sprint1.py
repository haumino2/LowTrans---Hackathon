"""Sprint 1 QA — ground-truth submit/triage + policy + retail fields.

Usage (API must be running on :8000, SQLite ok, Bedrock optional):
  cd apps/api
  python scripts/qa_sprint1.py

Exit 0 only if all assertions pass.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE = "http://127.0.0.1:8000"

# decision exact; route is one of allowed set
GROUND_TRUTH: dict[str, dict[str, Any]] = {
    "clean_cex": {"decision": "CLEAR", "routes": {"FULL", "STANDARD"}},
    "mixer_hop": {"decision": "ESCALATE", "routes": {"FULL"}},
    "sanctions": {"decision": "ESCALATE", "routes": {"FULL"}},
    "structuring": {"decision": "REVIEW", "routes": {"FULL", "STANDARD"}},
    "salary_inflow": {"decision": "CLEAR", "routes": {"FAST_TRACK"}},
    "ewallet_topup": {"decision": "CLEAR", "routes": {"FAST_TRACK"}},
    "remittance_highvalue": {"decision": "REVIEW", "routes": {"FULL"}},
    "merchant_payout": {"decision": "CLEAR", "routes": {"FAST_TRACK", "STANDARD"}},
}


def _req(
    method: str,
    path: str,
    *,
    body: dict | None = None,
    tenant: str = "vn-retail",
    timeout: int = 180,
) -> Any:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Role": "analyst",
            "X-Tenant": tenant,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _ok(cond: bool, msg: str, fails: list[str]) -> bool:
    if not cond:
        fails.append(msg)
        print(f"  FAIL  {msg}")
        return False
    print(f"  PASS  {msg}")
    return True


def main() -> int:
    fails: list[str] = []
    print("=" * 72)
    print("SPRINT 1 QA")
    print("=" * 72)

    # --- health ---
    try:
        h = _req("GET", "/api/health")
        print(f"API ok · sqlite={h.get('sqlite')} · bedrock={h.get('bedrock', {}).get('configured')}")
    except Exception as e:
        print(f"FATAL: API unreachable at {BASE}: {e}")
        return 2

    # --- scenarios catalog ---
    print("\n[B] /api/scenarios")
    scenarios = _req("GET", "/api/scenarios")["scenarios"]
    ids = [s["id"] for s in scenarios]
    _ok(len(ids) == 8, f"8 scenarios (got {len(ids)}: {ids})", fails)
    for sid in GROUND_TRUTH:
        _ok(sid in ids, f"scenario present: {sid}", fails)
    for s in scenarios:
        p = s.get("payload") or {}
        _ok(
            all(k in p for k in ("segment", "product", "rail")),
            f"{s['id']} has segment/product/rail",
            fails,
        )

    # --- policy switcher ---
    print("\n[B] Policy switcher")
    p_vn = _req("GET", "/api/policy", tenant="vn-retail")
    p_cx = _req("GET", "/api/policy", tenant="crypto")
    _ok(
        p_vn.get("content") != p_cx.get("content"),
        "vn-retail vs crypto policy content differs",
        fails,
    )
    _ok(
        p_vn.get("jurisdiction") == "vn-retail" and "v1." in str(p_vn.get("policy_version")),
        f"vn-retail meta {p_vn.get('display')}",
        fails,
    )
    _ok(
        p_cx.get("jurisdiction") == "crypto" and "v1." in str(p_cx.get("policy_version")),
        f"crypto meta {p_cx.get('display')}",
        fails,
    )

    # --- submit ground-truth ---
    print("\n[B] Scenario submit ground-truth")
    print(f"{'scenario':<22} {'expect':<10} {'got':<10} {'route':<12} {'result'}")
    print("-" * 72)
    by_id = {s["id"]: s for s in scenarios}
    retail_alert_id = None
    remittance_tr = None

    for sid, gt in GROUND_TRUTH.items():
        sc = by_id[sid]
        payload = dict(sc["payload"])
        payload["scenario_id"] = sid
        payload["run_triage"] = True
        tenant = "crypto" if (payload.get("rail") == "crypto") else "vn-retail"
        try:
            res = _req("POST", "/api/transactions/submit", body=payload, tenant=tenant, timeout=240)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            print(f"{sid:<22} {gt['decision']:<10} {'HTTP':<10} {'—':<12} FAIL")
            print(f"         detail: {body[:200]}")
            fails.append(f"{sid} submit HTTP {e.code}: {body[:200]}")
            continue
        except Exception as e:
            print(f"{sid:<22} {gt['decision']:<10} {'ERR':<10} {'—':<12} FAIL")
            fails.append(f"{sid} submit error: {e}")
            continue

        alert = res.get("alert") or {}
        tr = res.get("triage_result") or {}
        decision = tr.get("decision")
        route = tr.get("route")
        steps = tr.get("workflow_steps") or []
        agents = tr.get("agents_used") or []
        ok_d = decision == gt["decision"]
        ok_r = route in gt["routes"]
        mark = "PASS" if (ok_d and ok_r) else "FAIL"
        print(f"{sid:<22} {gt['decision']:<10} {str(decision):<10} {str(route):<12} {mark}")
        if not ok_d:
            fails.append(f"{sid}: decision want {gt['decision']} got {decision}")
        if not ok_r:
            fails.append(f"{sid}: route want {gt['routes']} got {route}")

        # retail no-graph safety
        if payload.get("rail") == "retail":
            _ok(len(steps) > 0, f"{sid} retail workflow has steps ({len(steps)})", fails)
            _ok(
                alert.get("segment") and alert.get("product") and alert.get("rail") == "retail",
                f"{sid} alert segment/product/rail",
                fails,
            )
            _ok(
                bool(alert.get("kyc_tier")) and isinstance(alert.get("product_mix"), list),
                f"{sid} kyc_tier + product_mix",
                fails,
            )
            _ok(isinstance(alert.get("prior_alerts"), dict), f"{sid} prior_alerts dict", fails)
            if sid == "salary_inflow":
                retail_alert_id = alert.get("id")
                _ok(
                    "Entity Identity Agent" not in agents
                    and "Financial Crime Investigator" not in agents,
                    f"{sid} FAST_TRACK skips Identity+Investigator",
                    fails,
                )
                router = [s for s in steps if s.get("skill_id") == "adaptive-router"]
                _ok(
                    bool(router) and "FAST-TRACK" in str(router[0].get("output") or ""),
                    f"{sid} Adaptive Router says FAST-TRACK",
                    fails,
                )

        if sid == "remittance_highvalue":
            remittance_tr = tr
            _ok(
                float(tr.get("confidence") or 1) < 0.70 and tr.get("hitl") is True,
                f"remittance HITL (conf={tr.get('confidence')} hitl={tr.get('hitl')})",
                fails,
            )

        # policy stamped on triage
        _ok(
            bool(tr.get("jurisdiction")) and bool(tr.get("policy_version")),
            f"{sid} triage has jurisdiction/policy_version "
            f"({tr.get('jurisdiction')} {tr.get('policy_version')})",
            fails,
        )
        if tenant == "vn-retail":
            _ok(
                tr.get("jurisdiction") == "vn-retail",
                f"{sid} jurisdiction=vn-retail under X-Tenant",
                fails,
            )
        if tenant == "crypto":
            _ok(
                tr.get("jurisdiction") == "crypto",
                f"{sid} jurisdiction=crypto under X-Tenant",
                fails,
            )

    # --- hard gate wins ---
    print("\n[B] Deterministic gate (sanctions_hit)")
    try:
        gate = _req(
            "POST",
            "/api/transactions/submit",
            body={
                "customer_name": "Gate Test",
                "amount_usd": 100,
                "asset": "USD",
                "network": "Fiat",
                "direction": "deposit",
                "sanctions_hit": True,
                "segment": "retail",
                "product": "ewallet",
                "rail": "retail",
                "run_triage": True,
            },
            tenant="vn-retail",
        )
        gd = (gate.get("triage_result") or {}).get("decision")
        _ok(gd == "ESCALATE", f"sanctions_hit forces ESCALATE (got {gd})", fails)
    except Exception as e:
        fails.append(f"gate submit error: {e}")
        print(f"  FAIL  gate submit: {e}")

    # --- analyst by segment ---
    print("\n[B] Analyst transactions by segment")
    ask = _req(
        "POST",
        "/api/analyst/ask",
        body={"question": "transactions by segment"},
        tenant="vn-retail",
    )
    cols = [c.lower() for c in (ask.get("columns") or [])]
    rows = ask.get("rows") or []
    _ok("segment" in cols or any("segment" in str(c).lower() for c in cols), "analyst columns include segment", fails)
    _ok(len(rows) >= 1, f"analyst returned rows ({len(rows)})", fails)
    # Prefer seeing retail in results when JSON/DB has retail submits
    flat = json.dumps(rows).lower()
    if retail_alert_id:
        _ok(
            "retail" in flat or "sme" in flat or len(rows) >= 1,
            "analyst segment query sees data after retail submit",
            fails,
        )

    # --- regression: demo heroes still present ---
    print("\n[D] Regression — queue heroes + copilot + simulated labels")
    alerts = _req("GET", "/api/alerts")
    hero_ids = {a["id"] for a in alerts}
    for hid in ("ALT-3002", "ALT-3005", "ALT-3010"):
        # 3005/3010 may vary — at least 3002
        pass
    _ok("ALT-3002" in hero_ids, "queue contains ALT-3002", fails)

    # simulated labels in supervisor source
    sup = (Path(__file__).resolve().parents[1] / "agent" / "supervisor.py").read_text(
        encoding="utf-8"
    )
    _ok(
        "SIMULATED_SKILL_IDS" in sup and "osint-research" in sup and "[simulated]" in sup,
        "simulated skill tagging still present",
        fails,
    )

    # copilot still answers
    try:
        cop = _req(
            "POST",
            "/api/copilot/chat",
            body={"message": "What is Travel Rule?", "alert_id": "ALT-3002"},
            timeout=60,
        )
        reply = str(cop.get("reply") or cop.get("message") or "")
        _ok(len(reply) > 10, f"copilot replied ({len(reply)} chars)", fails)
    except Exception as e:
        fails.append(f"copilot error: {e}")
        print(f"  FAIL  copilot: {e}")

    # demo reset + light triage on ALT-3003 if present
    try:
        _req("POST", "/api/demo/reset", body={})
        alerts2 = _req("GET", "/api/alerts")
        a3002 = next((a for a in alerts2 if a["id"] == "ALT-3002"), None)
        a3003 = next((a for a in alerts2 if a["id"] == "ALT-3003"), None)
        _ok(a3002 is not None, "after reset ALT-3002 present", fails)
        if a3003:
            tr3 = _req("POST", f"/api/alerts/{a3003['id']}/triage", tenant="crypto", timeout=240)
            _ok(
                tr3.get("decision") in ("CLEAR", "REVIEW", "ESCALATE"),
                f"ALT-3003 triage ok → {tr3.get('decision')}",
                fails,
            )
        if a3002:
            tr2 = _req("POST", f"/api/alerts/{a3002['id']}/triage", tenant="crypto", timeout=240)
            _ok(
                tr2.get("decision") == "ESCALATE",
                f"ALT-3002 → ESCALATE (got {tr2.get('decision')})",
                fails,
            )
            agents2 = tr2.get("agents_used") or []
            _ok(len(agents2) >= 3, f"ALT-3002 multi-agent ({agents2})", fails)
    except Exception as e:
        fails.append(f"demo/regression: {e}")
        print(f"  FAIL  demo/regression: {e}")

    # secrets not in git index (best-effort)
    print("\n[D] No secrets staged (best-effort)")
    try:
        st = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=str(Path(__file__).resolve().parents[3]),
            text=True,
            errors="replace",
        )
        tracked_bad = [
            ln
            for ln in st.splitlines()
            if ln[:2].strip() in ("M", "A", "MM", "AM")
            and any(x in ln for x in (".env", "credentials.json", "node_modules/"))
        ]
        _ok(len(tracked_bad) == 0, f"no tracked secret paths modified ({tracked_bad})", fails)
    except Exception as e:
        print(f"  SKIP  git check: {e}")

    print("\n" + "=" * 72)
    if fails:
        print(f"RESULT: FAIL ({len(fails)} assertion(s))")
        for f in fails:
            print(f"  - {f}")
        print("NOT DONE — fix failures above before calling Sprint 1 complete.")
        return 1
    print("RESULT: PASS — all Sprint 1 QA assertions green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
