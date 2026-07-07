from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ConnectorResult:
    """Standardized connector output with provenance."""

    data: dict
    source: str
    confidence: float  # 0..1


class SanctionsConnector(Protocol):
    def screen(self, *, name: str, alert: dict) -> ConnectorResult: ...


class OsintConnector(Protocol):
    def lookup(self, *, name: str, alert: dict | None) -> ConnectorResult: ...


class KybConnector(Protocol):
    def verify(self, *, partner: str, alert: dict) -> ConnectorResult: ...

