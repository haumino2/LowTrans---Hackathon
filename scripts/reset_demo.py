"""Reset alerts to pending for demo replay."""
import json
import urllib.error
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000"
DATA = Path(__file__).resolve().parents[1] / "data"


def reset_via_api() -> int | None:
    try:
        req = urllib.request.Request(f"{API}/api/demo/reset", method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            payload = json.loads(r.read().decode())
        return int(payload.get("alerts_reset", 0))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def reset_json_files() -> int:
    alerts_path = DATA / "alerts.json"
    alerts = json.loads(alerts_path.read_text(encoding="utf-8"))
    for a in alerts:
        a["status"] = "pending"
        a.pop("triage_result", None)
        a.pop("override", None)
        a.pop("supervisor_approval", None)
        a.pop("assigned_to", None)
        a.pop("notes", None)
        a.pop("case_id", None)
        a.pop("case_state", None)
        a.pop("case_assigned_to", None)
        a.pop("case_notes", None)
    alerts_path.write_text(json.dumps(alerts, indent=2), encoding="utf-8")

    audit_path = DATA / "audit_log.jsonl"
    if audit_path.exists():
        audit_path.write_text("", encoding="utf-8")
    return len(alerts)


def main():
    count = reset_via_api()
    if count is not None:
        print(f"Reset {count} alerts via API (SQLite/DB). Audit log cleared.")
        return
    count = reset_json_files()
    print(f"Reset {count} alerts in JSON files. Audit log cleared.")
    print("Tip: start API and use POST /api/demo/reset when DB is enabled.")


if __name__ == "__main__":
    main()
