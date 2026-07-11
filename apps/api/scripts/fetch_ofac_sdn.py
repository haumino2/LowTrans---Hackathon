"""Download the public OFAC SDN list and cache it as data/ofac_sdn.json.

Sources (US Treasury Sanctions List Service — free, no API key):
  - SDN.CSV  primary names + programs
  - ALT.CSV  aliases / AKAs

Offline: if download fails, keep the existing cache and exit 0 when a cache
is present; exit 1 only when neither download nor cache is available.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_DATA = Path(__file__).resolve().parents[3] / "data"
OUT_PATH = REPO_DATA / "ofac_sdn.json"

SDN_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV"
ALT_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ALT.CSV"
# Legacy redirect still works for some environments
SDN_URL_FALLBACK = "https://www.treasury.gov/ofac/downloads/sdn.csv"
ALT_URL_FALLBACK = "https://www.treasury.gov/ofac/downloads/alt.csv"

USER_AGENT = (
    "Mozilla/5.0 (compatible; ClarioOFACFetcher/1.0; +https://github.com/clario) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
TIMEOUT_S = 60


def _fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv,*/*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return resp.read()


def _download(url: str, fallback: str) -> bytes:
    try:
        return _fetch_bytes(url)
    except (urllib.error.URLError, TimeoutError, OSError) as first:
        try:
            return _fetch_bytes(fallback)
        except (urllib.error.URLError, TimeoutError, OSError):
            raise first


def _parse_sdn_csv(raw: bytes) -> dict[str, dict]:
    """Return ent_num -> {name, program, type, aliases}."""
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    by_uid: dict[str, dict] = {}
    for row in reader:
        if not row or len(row) < 4:
            continue
        # Skip header if present
        if row[0].strip().lower() in ("ent_num", "uid", "number"):
            continue
        uid = row[0].strip().strip('"')
        name = row[1].strip().strip('"')
        sdn_type = row[2].strip().strip('"') if len(row) > 2 else ""
        program = row[3].strip().strip('"') if len(row) > 3 else ""
        if not uid or not name:
            continue
        by_uid[uid] = {
            "uid": uid,
            "name": name,
            "aliases": [],
            "program": program,
            "type": sdn_type,
        }
    return by_uid


def _merge_alt_csv(by_uid: dict[str, dict], raw: bytes) -> None:
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if not row or len(row) < 4:
            continue
        if row[0].strip().lower() in ("ent_num", "uid", "number"):
            continue
        uid = row[0].strip().strip('"')
        alt_name = row[3].strip().strip('"')
        if not uid or not alt_name or uid not in by_uid:
            continue
        aliases: list[str] = by_uid[uid]["aliases"]
        if alt_name not in aliases and alt_name != by_uid[uid]["name"]:
            aliases.append(alt_name)


def build_payload(sdn_raw: bytes, alt_raw: bytes | None) -> dict:
    by_uid = _parse_sdn_csv(sdn_raw)
    if alt_raw:
        _merge_alt_csv(by_uid, alt_raw)
    entries = sorted(by_uid.values(), key=lambda e: e["name"].lower())
    return {
        "downloaded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "OFAC SDN (public list)",
        "source_urls": [SDN_URL, ALT_URL],
        "entry_count": len(entries),
        "entries": entries,
    }


def load_cache(path: Path = OUT_PATH) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("entries"), list):
            return data
    except (OSError, json.JSONDecodeError):
        return None
    return None


def main() -> int:
    REPO_DATA.mkdir(parents=True, exist_ok=True)
    try:
        print(f"Downloading SDN.CSV from {SDN_URL} ...")
        sdn_raw = _download(SDN_URL, SDN_URL_FALLBACK)
        print(f"  SDN.CSV: {len(sdn_raw):,} bytes")
        alt_raw: bytes | None = None
        try:
            print(f"Downloading ALT.CSV from {ALT_URL} ...")
            alt_raw = _download(ALT_URL, ALT_URL_FALLBACK)
            print(f"  ALT.CSV: {len(alt_raw):,} bytes")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  ALT.CSV download failed ({e}); continuing with primary names only.")
        payload = build_payload(sdn_raw, alt_raw)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"Wrote {payload['entry_count']:,} entries -> {OUT_PATH}")
        return 0
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        cached = load_cache()
        if cached:
            n = cached.get("entry_count") or len(cached.get("entries") or [])
            print(
                f"Download failed ({e}). Using cached list "
                f"({n:,} entries, downloaded_at={cached.get('downloaded_at', '?')})."
            )
            return 0
        print(f"Download failed and no cache at {OUT_PATH}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
