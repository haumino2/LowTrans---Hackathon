from __future__ import annotations

from functools import lru_cache

from agent.connectors.base import KybConnector, OsintConnector, SanctionsConnector
from agent.connectors.mock import MockKybConnector, MockOsintConnector, MockSanctionsConnector


@lru_cache
def sanctions_connector() -> SanctionsConnector:
    return MockSanctionsConnector()


@lru_cache
def osint_connector() -> OsintConnector:
    return MockOsintConnector()


@lru_cache
def kyb_connector() -> KybConnector:
    return MockKybConnector()

