"""Amazon Bedrock client — chat (Nova) + embeddings (Cohere).

Env vars:
  AWS_REGION=us-east-1
  BEDROCK_MODEL_ID=global.amazon.nova-2-lite-v1:0
  BEDROCK_EMBED_MODEL_ID=cohere.embed-english-v3
  AWS_BEARER_TOKEN_BEDROCK=<long-term API key from console>
"""

from __future__ import annotations

import json
import os
from typing import Any, Literal

import boto3
import numpy as np
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "global.amazon.nova-2-lite-v1:0")
EMBED_MODEL_ID = os.getenv("BEDROCK_EMBED_MODEL_ID", "cohere.embed-english-v3")

_client = None


def get_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    return _client


def is_configured() -> bool:
    """True if Bedrock credentials appear available."""
    if os.getenv("AWS_BEARER_TOKEN_BEDROCK"):
        return True
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        return True
    # Default credential chain (AWS CLI profile, IAM role on ECS)
    try:
        import botocore.session

        creds = botocore.session.get_session().get_credentials()
        return creds is not None
    except Exception:
        return False


def invoke_claude(
    user_message: str,
    system: str = "",
    max_tokens: int = 2048,
    temperature: float = 0.2,
) -> str:
    """Invoke a Bedrock chat model via Converse API (Nova, Claude, etc.)."""
    client = get_client()
    messages = [{"role": "user", "content": [{"text": user_message}]}]
    kwargs: dict[str, Any] = {
        "modelId": MODEL_ID,
        "messages": messages,
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
    }
    if system:
        kwargs["system"] = [{"text": system}]

    response = client.converse(**kwargs)
    return response["output"]["message"]["content"][0]["text"]


EmbedInputType = Literal["search_document", "search_query", "classification", "clustering"]


def embed_texts(
    texts: list[str],
    input_type: EmbedInputType = "search_document",
) -> list[list[float]]:
    """Get text embeddings via Cohere on Bedrock."""
    if not texts:
        return []
    client = get_client()
    body = {"texts": texts, "input_type": input_type}
    response = client.invoke_model(
        modelId=EMBED_MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
    )
    payload = json.loads(response["body"].read())
    return payload["embeddings"]


def cosine_scores(query_vec: list[float], matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity between one query vector and a matrix of vectors."""
    q = np.array(query_vec, dtype=float).reshape(1, -1)
    return np.dot(matrix, q.T).flatten() / (
        np.linalg.norm(matrix, axis=1) * np.linalg.norm(q) + 1e-9
    )


def health_check(*, live: bool = False) -> dict[str, Any]:
    """Config check; set live=True to run minimal chat + embed probes."""
    result: dict[str, Any] = {
        "configured": is_configured(),
        "region": AWS_REGION,
        "model_id": MODEL_ID,
        "embed_model_id": EMBED_MODEL_ID,
        "token_set": bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK")),
    }
    if live and result["configured"]:
        try:
            reply = invoke_claude("Reply with exactly: OK", max_tokens=8)
            result["chat_live"] = True
            result["chat_sample"] = reply[:80]
        except (ClientError, BotoCoreError, RuntimeError) as e:
            result["chat_live"] = False
            result["chat_error"] = str(e)
        try:
            vec = embed_texts(["AML test"], input_type="search_query")[0]
            result["embed_live"] = True
            result["embed_dims"] = len(vec)
        except (ClientError, BotoCoreError, RuntimeError) as e:
            result["embed_live"] = False
            result["embed_error"] = str(e)
    return result


def safe_invoke(user_message: str, system: str = "", fallback: str = "") -> str:
    """Invoke with graceful fallback for demo stability."""
    try:
        return invoke_claude(user_message, system=system)
    except (ClientError, BotoCoreError, KeyError, json.JSONDecodeError) as e:
        if fallback:
            return fallback
        raise RuntimeError(f"Bedrock invoke failed: {e}") from e
