"""Case and policy tools."""

from __future__ import annotations

from typing import Any

from db.repository import DATA_DIR, get_alert, load_resolved_cases


def read_alert(alert_id: str) -> dict[str, Any] | None:
    return get_alert(alert_id)


def read_policy(tenant_id: str | None = None) -> str:
    """Load policy for a tenant; falls back to default policy.md."""
    if tenant_id:
        p = DATA_DIR / f"policy.{tenant_id}.md"
        if p.exists():
            return p.read_text(encoding="utf-8")
    return (DATA_DIR / "policy.md").read_text(encoding="utf-8")


def list_cases(limit: int = 15) -> list[dict[str, Any]]:
    return load_resolved_cases()[:limit]
