"""Shared investigation state for the 4-node agent graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Decision = Literal["CLEAR", "REVIEW", "ESCALATE"]
Priority = Literal["critical", "high", "normal", "low"]


@dataclass
class InvestigationState:
    alert: dict[str, Any]
    priority: Priority = "normal"
    sla_bucket: str = "standard"
    session_context: list[dict[str, Any]] = field(default_factory=list)
    similar_cases: list[dict[str, Any]] = field(default_factory=list)
    entity_findings: list[dict[str, Any]] = field(default_factory=list)
    financial_findings: list[dict[str, Any]] = field(default_factory=list)
    policy_hits: list[dict[str, Any]] = field(default_factory=list)
    ml_score: dict[str, Any] | None = None
    decision: Decision = "REVIEW"
    confidence: float = 0.65
    disposition: str = "analyst_review"
    rationale: list[str] = field(default_factory=list)
    agents_used: list[str] = field(default_factory=list)
    workflow_steps: list[dict[str, Any]] = field(default_factory=list)
    sar_draft: str | None = None
    sar_mode: str | None = None  # "LLM" | "template" when SAR drafted
    audit_pack: dict[str, Any] = field(default_factory=dict)
    explainability: list[dict[str, Any]] = field(default_factory=list)
    hard_escalate: bool = False

    def add_agent(self, name: str) -> None:
        if name not in self.agents_used:
            self.agents_used.append(name)

    def to_result(self) -> dict[str, Any]:
        steps = self.workflow_steps
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "signals_reviewed": [
                "kyt_score",
                "travel_rule",
                "wallet_age",
                "mixer_exposure",
                "sanctions_screening",
                "counterparty",
                "amount_usd",
                "risk_tags",
                "ml_validate",
            ],
            "similar_cases": self.similar_cases,
            "agents_used": list(self.agents_used),
            "suggested_disposition": self.disposition,
            "escalation_summary": self.sar_draft,
            "explainability": self.explainability,
            "rag_enabled": True,
            "policy_version": "v1.0",
            "priority": self.priority,
            "sla_bucket": self.sla_bucket,
            "ml_score": self.ml_score,
            "entity_findings": self.entity_findings,
            "financial_findings": self.financial_findings,
            "policy_hits": self.policy_hits,
            "audit_pack": self.audit_pack,
            "workflow_steps": steps,
            "workflow_summary": {
                "total_steps": len(steps),
                "agents_run": len(
                    [s for s in steps if s.get("status") == "completed" and s.get("agent") != "Alert Ingestion"]
                ),
                "agents_skipped": len([s for s in steps if s.get("status") == "skipped"]),
                "total_duration_ms": sum(int(s.get("duration_ms", 0)) for s in steps),
            },
        }
