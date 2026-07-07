#!/usr/bin/env python3
"""Pre-flight checks before hackathon demo."""

from __future__ import annotations

import json
import sys
import urllib.request

API = "http://localhost:8000"


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print("LowTrans pre-flight\n")
    failed = 0

    try:
        with urllib.request.urlopen(f"{API}/api/health", timeout=5) as r:
            health = json.loads(r.read().decode())
        check("API health", health.get("status") == "ok")
        check("RAG cases", health.get("rag_cases_loaded", 0) >= 10, str(health.get("rag_cases_loaded")))
        check("DB", health.get("db_connected") is True, health.get("db_backend", ""))
        check("RAG backend", bool(health.get("rag_backend")), str(health.get("rag_backend", "")))
        check("Agents registered", health.get("agents_registered", 0) >= 6, str(health.get("agents_registered")))
        bedrock = health.get("bedrock", {})
        check("Bedrock configured", bedrock.get("configured") is True, bedrock.get("model_id", "n/a"))
    except Exception as e:
        check("API health", False, str(e))
        failed += 1

    try:
        with urllib.request.urlopen(f"{API}/api/alerts", timeout=5) as r:
            alerts = json.loads(r.read().decode())
        check("Alerts loaded", len(alerts) >= 10, str(len(alerts)))
    except Exception as e:
        check("Alerts loaded", False, str(e))
        failed += 1

    if health.get("db_backend") == "postgres" and health.get("rag_backend") != "pgvector":
        print("\nTip: run `npm run db:seed` to load pgvector embeddings.")
    print("\nRun: python scripts/reset_demo.py if queue is empty or stale.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
