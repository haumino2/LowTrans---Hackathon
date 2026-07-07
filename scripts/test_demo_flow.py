#!/usr/bin/env python3
"""End-to-end demo flow test for ALT-3002."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:8000"
ALERT_ID = "ALT-3002"


def get(path: str, headers: dict | None = None) -> dict | list:
    req = urllib.request.Request(API + path, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def post(path: str, body: dict | None = None, headers: dict | None = None) -> dict:
    h = {"Content-Type": "application/json", **(headers or {})}
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(API + path, data=data, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main() -> int:
    failed = 0

    print("=== 1. Get ALT-3002 ===")
    alert = get(f"/api/alerts/{ALERT_ID}")
    print(f"  customer: {alert['customer_name']} | status: {alert['status']} | kyt: {alert['kyt_score']}")

    print("=== 2. Triage ALT-3002 ===")
    result = post(f"/api/alerts/{ALERT_ID}/triage", headers={"X-Role": "analyst"})
    decision = result["decision"]
    print(f"  decision: {decision} | confidence: {result['confidence']}")
    print(f"  agents: {result.get('agents_used', [])}")
    steps = result.get("workflow_steps", [])
    print(f"  workflow steps: {len(steps)}")
    if decision != "ESCALATE":
        print(f"  WARN: expected ESCALATE for Brooke demo, got {decision}")

    print("=== 3. Graph ===")
    graph = get(f"/api/alerts/{ALERT_ID}/graph")
    print(f"  nodes: {len(graph.get('nodes', []))} | flagged: {graph.get('flagged_node_ids', [])}")

    print("=== 4. Copilot ===")
    cop = post(
        "/api/copilot/chat",
        {"message": "Summarize risk for this alert", "alert_id": ALERT_ID},
        headers={"X-Role": "analyst"},
    )
    reply = cop.get("reply", "")[:120]
    print(f"  skill: {cop.get('skill_name')} | reply: {reply}...")

    print("=== 5. Override (analyst) ===")
    ov = post(
        f"/api/alerts/{ALERT_ID}/override",
        {"decision": "REVIEW", "reason": "Demo override test"},
        headers={"X-Role": "analyst"},
    )
    print(f"  override ok: {ov.get('ok')}")

    print("=== 6. Override blocked (auditor) ===")
    try:
        post(
            f"/api/alerts/{ALERT_ID}/override",
            {"decision": "CLEAR", "reason": "should fail"},
            headers={"X-Role": "auditor"},
        )
        print("  FAIL: auditor should be blocked")
        failed += 1
    except urllib.error.HTTPError as e:
        print(f"  blocked as expected: HTTP {e.code}")

    print("=== 7. Audit ===")
    audit = get("/api/audit")
    print(f"  audit entries: {len(audit)}")
    for e in audit[-3:]:
        et = e.get("event_type", "?")
        d = e.get("decision", e.get("override_decision", ""))
        print(f"    - {et}: {d}")

    print("=== 8. SSE stream ===")
    req = urllib.request.Request(API + f"/api/alerts/{ALERT_ID}/triage/stream")
    with urllib.request.urlopen(req, timeout=60) as r:
        events = []
        for _ in range(8):
            line = r.readline().decode()
            if line.startswith("data:"):
                events.append(json.loads(line[5:].strip()))
        print(f"  events: {len(events)} | last event: {events[-1].get('event') if events else 'none'}")

    print()
    if failed:
        print("=== DEMO API FLOW: FAIL ===")
        return 1
    print("=== DEMO API FLOW: PASS ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
