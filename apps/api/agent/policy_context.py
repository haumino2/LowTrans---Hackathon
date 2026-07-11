"""Resolve tenant-scoped policy markdown + version metadata."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

# Canonical demo tenants (X-Tenant / clario_tenant values)
KNOWN_TENANTS: dict[str, dict[str, str]] = {
    "vn-retail": {
        "jurisdiction": "vn-retail",
        "policy_version": "v1.1",
        "label": "VN Retail",
    },
    "crypto": {
        "jurisdiction": "crypto",
        "policy_version": "v1.2",
        "label": "Crypto / VASP",
    },
    "default": {
        "jurisdiction": "default",
        "policy_version": "v1.0",
        "label": "Default",
    },
    "demo": {
        "jurisdiction": "default",
        "policy_version": "v1.0",
        "label": "Default",
    },
}


def normalize_tenant(raw: str | None) -> str:
    tid = (raw or os.getenv("LOWTRANS_TENANT") or "default").strip().lower()
    if tid in ("", "demo"):
        return "default"
    return tid


def _parse_front_meta(content: str) -> dict[str, str]:
    """Pull Version / Jurisdiction lines from policy markdown header."""
    out: dict[str, str] = {}
    for line in content.splitlines()[:12]:
        m = re.match(r"\*\*Jurisdiction:\*\*\s*(.+)", line.strip(), re.I)
        if m:
            out["jurisdiction"] = m.group(1).strip()
        m = re.match(r"\*\*Version:\*\*\s*(.+)", line.strip(), re.I)
        if m:
            out["policy_version"] = m.group(1).strip()
        m = re.match(r"^#\s+.+?\s+(v[\d.]+)\s*$", line.strip(), re.I)
        if m and "policy_version" not in out:
            out["policy_version"] = m.group(1)
    return out


def resolve_policy(tenant: str | None = None) -> dict[str, Any]:
    """Load policy.{tenant}.md or fall back to policy.md."""
    tid = normalize_tenant(tenant)
    path = DATA_DIR / f"policy.{tid}.md"
    used_tenant = tid
    if not path.exists():
        path = DATA_DIR / "policy.md"
        used_tenant = "default"
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    meta = dict(KNOWN_TENANTS.get(used_tenant) or KNOWN_TENANTS["default"])
    parsed = _parse_front_meta(content)
    if parsed.get("jurisdiction"):
        meta["jurisdiction"] = parsed["jurisdiction"]
    if parsed.get("policy_version"):
        meta["policy_version"] = parsed["policy_version"]
    return {
        "tenant": used_tenant,
        "jurisdiction": meta["jurisdiction"],
        "policy_version": meta["policy_version"],
        "label": meta.get("label") or used_tenant,
        "content": content,
        "display": f"policy: {meta['jurisdiction']} {meta['policy_version']}",
    }


def stamp_alert_policy(alert: dict[str, Any], tenant: str | None) -> dict[str, Any]:
    """Attach active jurisdiction / policy_version onto the alert for triage."""
    meta = resolve_policy(tenant)
    alert = dict(alert)
    alert["jurisdiction"] = meta["jurisdiction"]
    alert["policy_version"] = meta["policy_version"]
    alert["_policy_tenant"] = meta["tenant"]
    return alert
