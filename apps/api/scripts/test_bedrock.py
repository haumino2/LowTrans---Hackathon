"""Quick Bedrock connectivity test. Run from apps/api:

    python scripts/test_bedrock.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.bedrock import embed_texts, health_check, invoke_claude
from agent.rag import rag_engine


def main() -> int:
    info = health_check()
    print("Bedrock config:", info)
    print("RAG backend:", rag_engine.backend)
    if not info["configured"]:
        print("\nMissing AWS_BEARER_TOKEN_BEDROCK in .env")
        return 1

    ok = True

    try:
        vec = embed_texts(["AML mixer exposure alert"], input_type="search_query")[0]
        print(f"\nEMBED OK: {len(vec)} dimensions")
    except Exception as e:
        ok = False
        print("\nEMBED FAILED:", e)

    try:
        reply = invoke_claude("Reply with exactly: OK", max_tokens=16)
        print("CHAT OK:", reply.strip())
    except Exception as e:
        ok = False
        print("CHAT FAILED:", e)
        if "Throttling" in str(e):
            print("  (Nova daily limit hit — retry later or use Cohere embed + TF-IDF fallback)")

    if rag_engine.backend == "cohere":
        sample = rag_engine.find_similar(
            {
                "customer_name": "Test",
                "direction": "withdrawal",
                "amount_usd": 5000,
                "asset": "ETH",
                "network": "ethereum",
                "kyt_score": 72,
                "risk_tags": ["mixer_exposure"],
                "travel_rule_status": "pending",
                "counterparty": "unknown",
                "signals": {"wallet_age_days": 5, "mixer_exposure": 0.8, "sanctions_hit": False},
                "risk_level": "high",
            },
            top_k=2,
        )
        print("RAG OK:", [c["case_id"] for c in sample])

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
