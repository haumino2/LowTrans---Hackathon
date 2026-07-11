"""Real OFAC SDN screening against the public list cached in data/ofac_sdn.json."""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[4] / "data"
OFAC_PATH = DATA_DIR / "ofac_sdn.json"

# Fuzzy score in [0, 1]. Industry-style auto-hit threshold for demo screening.
HIT_THRESHOLD = 0.85

_HAS_RAPIDFUZZ = False
try:
    from rapidfuzz import fuzz as _rf_fuzz
    from rapidfuzz import process as _rf_process

    _HAS_RAPIDFUZZ = True
except ImportError:
    _rf_fuzz = None  # type: ignore[assignment]
    _rf_process = None  # type: ignore[assignment]


_NORMALIZE_RE = re.compile(r"[^a-z0-9\s]+")
_SPACE_RE = re.compile(r"\s+")


def _normalize(s: str) -> str:
    s = (s or "").lower().strip()
    s = _NORMALIZE_RE.sub(" ", s)
    return _SPACE_RE.sub(" ", s).strip()


@lru_cache(maxsize=1)
def _load_index(path: str | None = None) -> tuple[list[dict[str, Any]], list[str], list[int]]:
    """Load entries plus a flat name/alias corpus for fuzzy search.

    Returns (entries, corpus_strings, corpus_entry_index).
    """
    p = Path(path) if path else OFAC_PATH
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return [], [], []
    raw = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return [], [], []

    entries: list[dict[str, Any]] = []
    corpus: list[str] = []
    corpus_idx: list[int] = []
    for ent in raw:
        if not isinstance(ent, dict) or not ent.get("name"):
            continue
        ei = len(entries)
        entries.append(ent)
        primary = _normalize(str(ent["name"]))
        if primary:
            corpus.append(primary)
            corpus_idx.append(ei)
        for alias in ent.get("aliases") or []:
            a = _normalize(str(alias))
            if a:
                corpus.append(a)
                corpus_idx.append(ei)
    return entries, corpus, corpus_idx


def load_ofac_list(path: str | None = None) -> list[dict[str, Any]]:
    """Load SDN entries from cache. Empty list if missing/corrupt (never raises)."""
    entries, _, _ = _load_index(path)
    return entries


def ofac_available() -> bool:
    return bool(load_ofac_list())


def _best_match(query: str, path: str | None = None) -> dict[str, Any]:
    """Return best fuzzy match across primary names and aliases."""
    entries, corpus, corpus_idx = _load_index(path)
    q = _normalize(query)
    empty = {
        "hit": False,
        "score": 0.0,
        "matched_name": None,
        "program": None,
        "query": query,
        "matched_field": None,
        "uid": None,
    }
    if not q or len(q) < 2 or not entries or not corpus:
        return empty

    best_score = 0.0
    best_ei = -1
    best_field = "name"
    matched_surface = ""

    if _HAS_RAPIDFUZZ and _rf_process is not None and _rf_fuzz is not None:
        result = _rf_process.extractOne(
            q,
            corpus,
            scorer=_rf_fuzz.token_sort_ratio,
            score_cutoff=1,
        )
        if result is not None:
            matched_surface, raw_score, corpus_pos = result
            best_score = float(raw_score) / 100.0
            best_ei = corpus_idx[corpus_pos]
            ent = entries[best_ei]
            best_field = "name" if _normalize(str(ent.get("name") or "")) == matched_surface else "alias"
    else:
        for i, surface in enumerate(corpus):
            score = SequenceMatcher(None, q, surface).ratio()
            if score > best_score:
                best_score = score
                best_ei = corpus_idx[i]
                matched_surface = surface
                ent = entries[best_ei]
                best_field = "name" if _normalize(str(ent.get("name") or "")) == surface else "alias"
                if score >= 0.995:
                    break

    if best_ei < 0:
        return empty

    best = entries[best_ei]
    hit = best_score >= HIT_THRESHOLD
    return {
        "hit": hit,
        "score": round(best_score, 4),
        "matched_name": best.get("name"),
        "program": best.get("program"),
        "query": query,
        "matched_field": best_field,
        "uid": best.get("uid"),
        "sdn_type": best.get("type"),
        "matched_surface": matched_surface or None,
    }


def screen_ofac(
    name: str | None = None,
    counterparty: str | None = None,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    """Fuzzy-match customer name and/or counterparty against OFAC SDN.

    Returns:
      {
        hit: bool,
        score: float,           # best score across queries [0,1]
        matched_name: str|None,
        program: str|None,
        ...
      }
    """
    entries = load_ofac_list(path)
    queries = [q for q in (name, counterparty) if q and str(q).strip()]
    if not entries:
        return {
            "hit": False,
            "score": 0.0,
            "matched_name": None,
            "program": None,
            "source": "OFAC SDN (public list)",
            "list_available": False,
            "queries": queries,
            "candidates": [],
        }

    candidates: list[dict[str, Any]] = []
    for q in queries:
        candidates.append(_best_match(str(q), path=path))

    best = max(candidates, key=lambda c: float(c.get("score") or 0)) if candidates else {
        "hit": False,
        "score": 0.0,
        "matched_name": None,
        "program": None,
    }

    return {
        "hit": bool(best.get("hit")),
        "score": float(best.get("score") or 0.0),
        "matched_name": best.get("matched_name"),
        "program": best.get("program"),
        "source": "OFAC SDN (public list)",
        "list_available": True,
        "entry_count": len(entries),
        "threshold": HIT_THRESHOLD,
        "queries": queries,
        "candidates": candidates,
        "uid": best.get("uid"),
        "matched_field": best.get("matched_field"),
        "sdn_type": best.get("sdn_type"),
    }


def clear_ofac_cache() -> None:
    """Drop in-memory list (e.g. after re-fetch)."""
    _load_index.cache_clear()
