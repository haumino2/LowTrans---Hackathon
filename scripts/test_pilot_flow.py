#!/usr/bin/env python3
"""Pilot readiness regression: approvals, notes, metrics, copilot stream."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:8000"


def _req(path: str, method: str = "GET", body: dict | None = None, headers: dict | None = None):
    h = {"Content-Type": "application/json", **(headers or {})}
    data = json.dumps(body).encode() if body is not None else None
    return urllib.request.Request(API + path, data=data, headers=h, method=method)


def _json(req: urllib.request.Request, timeout: int = 60):
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main() -> int:
    failed = 0

    print("=== reset ===")
    print(_json(_req("/api/demo/reset", method="POST")))

    print("=== metrics ===")
    m = _json(_req("/api/metrics"))
    print("requests_total", m.get("requests_total"))

    print("=== triage ALT-3002 ===")
    tri = _json(_req("/api/alerts/ALT-3002/triage", method="POST", headers={"X-Role": "analyst"}))
    print("decision", tri.get("decision"))

    a = _json(_req("/api/alerts/ALT-3002"))
    print("status", a.get("status"))
    if a.get("status") != "escalate_pending":
        print("FAIL: expected escalate_pending")
        failed += 1

    print("=== approvals inbox (supervisor) ===")
    inbox = _json(_req("/api/approvals", headers={"X-Role": "supervisor"}))
    print("pending approvals", len(inbox))
    if not any(x.get("id") == "ALT-3002" for x in inbox):
        print("FAIL: ALT-3002 not in approvals inbox")
        failed += 1

    print("=== assign + note ===")
    _json(_req("/api/alerts/ALT-3002/assign", method="POST", body={"assignee": "alice@vasp.com"}, headers={"X-Role": "analyst"}))
    _json(_req("/api/alerts/ALT-3002/notes", method="POST", body={"note": "Pilot note: review sanctions fuzzy match"}, headers={"X-Role": "analyst"}))
    a2 = _json(_req("/api/alerts/ALT-3002"))
    print("assigned_to", a2.get("assigned_to"), "notes", len(a2.get("notes") or []))

    print("=== approve escalation ===")
    _json(_req("/api/alerts/ALT-3002/approve-escalation", method="POST", body={}, headers={"X-Role": "supervisor"}))
    a3 = _json(_req("/api/alerts/ALT-3002"))
    print("status", a3.get("status"))
    if a3.get("status") != "escalate":
        print("FAIL: expected escalate")
        failed += 1

    print("=== copilot stream smoke ===")
    stream_req = _req(
        "/api/copilot/chat/stream",
        method="POST",
        body={"message": "Screening status for this alert", "alert_id": "ALT-3002", "session_id": "copilot-ALT-3002"},
        headers={"X-Role": "analyst"},
    )
    try:
        with urllib.request.urlopen(stream_req, timeout=30) as r:
            events = []
            for _ in range(60):
                line = r.readline().decode()
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()).get("event"))
                    if "done" in events:
                        break
        print("events", events[:5], "... last", events[-1] if events else None)
        if not events or events[-1] != "done":
            print("FAIL: stream did not finish")
            failed += 1
    except urllib.error.URLError as e:
        print("FAIL: stream error", e)
        failed += 1

    print("\n=== RESULT ===")
    if failed:
        print("FAIL", failed)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

