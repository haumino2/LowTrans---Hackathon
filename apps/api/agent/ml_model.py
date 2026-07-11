"""Sklearn KYT risk model — trained on synthetic + demo alerts, explainable via importances."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

FEATURE_NAMES = [
    "amount_norm",
    "mixer",
    "sanctions",
    "pep",
    "travel_gap",
    "structuring",
    "graph_norm",
    "new_wallet",
    "device_anomaly",
    "hri",
    "account_age_norm",
]

_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
_MODEL_PATH = _DATA_DIR / "models" / "kyt_gb.joblib"

_model = None
_model_meta: dict[str, Any] = {}


def raw_feature_dict(alert: dict[str, Any]) -> dict[str, float]:
    signals = alert.get("signals") or {}
    sanctions = alert.get("sanctions_screening") or {}
    tags = set(alert.get("risk_tags") or [])
    amount = float(alert.get("amount_usd") or 0)
    travel = str(alert.get("travel_rule_status", "")).lower()
    connections = int(alert.get("connections") or 0)
    wallet_age = int(signals.get("wallet_age_days") or alert.get("account_age_days") or 0)
    account_age = int(alert.get("account_age_days") or wallet_age or 0)

    sanctions_v = 1.0 if (
        signals.get("sanctions_hit") or str(sanctions.get("status", "")).lower() == "hit"
    ) else (0.5 if str(sanctions.get("status", "")).lower() == "review" else 0.0)

    travel_v = 1.0 if travel == "missing" else (0.6 if travel in ("incomplete", "mismatch") else 0.0)
    structuring = 1.0 if ("structuring" in tags or signals.get("structuring")) else 0.0
    if not structuring and 9000 <= amount <= 9999:
        structuring = 0.7

    device_risk = str(signals.get("device_risk", "low")).lower()
    device = 1.0 if device_risk == "high" else (0.5 if device_risk == "medium" else 0.0)
    country = str(alert.get("country") or "")
    ip_c = str(signals.get("ip_country") or "")
    if ip_c and country and ip_c.lower() not in country.lower() and country.lower() not in ip_c.lower():
        # rough mismatch (US vs United States still ok-ish)
        if len(ip_c) == 2 and len(country) > 2:
            pass
        elif ip_c != country:
            device = max(device, 0.7)

    return {
        "amount_norm": min(amount / 100000.0, 1.5),
        "mixer": 1.0 if (signals.get("mixer_exposure") or "mixer_exposure" in tags) else 0.0,
        "sanctions": sanctions_v,
        "pep": 1.0 if signals.get("pep_hit") else 0.0,
        "travel_gap": travel_v,
        "structuring": structuring,
        "graph_norm": min(connections / 20.0, 1.5),
        "new_wallet": 1.0 if (wallet_age < 7 or "new_wallet" in tags) else (0.4 if wallet_age < 30 else 0.0),
        "device_anomaly": device,
        "hri": 1.0 if "high_risk_jurisdiction" in tags else 0.0,
        "account_age_norm": min(account_age / 365.0, 2.0),
    }


def vectorize(alert: dict[str, Any]) -> np.ndarray:
    d = raw_feature_dict(alert)
    return np.array([[d[n] for n in FEATURE_NAMES]], dtype=float)


def _label_from_alert(alert: dict[str, Any]) -> float:
    """Continuous 0–100 target for training."""
    kyt = alert.get("kyt_score")
    if kyt is not None:
        return float(kyt)
    level = str(alert.get("risk_level", "low")).lower()
    return {"high": 80.0, "medium": 50.0, "low": 20.0}.get(level, 40.0)


def _synthetic_rows(n: int = 400, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X = []
    y = []
    for _ in range(n):
        amount = float(rng.choice([800, 2500, 9500, 15000, 32000, 55000, 90000]))
        mixer = float(rng.random() < 0.18)
        sanctions = float(rng.choice([0.0, 0.0, 0.0, 0.5, 1.0], p=[0.75, 0.05, 0.05, 0.08, 0.07]))
        pep = float(rng.random() < 0.08)
        travel = float(rng.choice([0.0, 0.6, 1.0], p=[0.7, 0.15, 0.15]))
        structuring = float(rng.random() < 0.1)
        if 9000 <= amount <= 9999:
            structuring = max(structuring, 0.7)
        graph = float(rng.uniform(0, 1.2))
        new_w = float(rng.choice([0.0, 0.4, 1.0], p=[0.6, 0.25, 0.15]))
        device = float(rng.choice([0.0, 0.5, 1.0], p=[0.7, 0.2, 0.1]))
        hri = float(rng.random() < 0.12)
        age = float(rng.uniform(0.02, 2.0))
        row = [amount / 100000.0, mixer, sanctions, pep, travel, structuring, graph, new_w, device, hri, age]
        # Teacher score mirrors policy intuition
        score = (
            min(amount / 100000.0, 1.2) * 22
            + mixer * 24
            + sanctions * 28
            + pep * 10
            + travel * 16
            + structuring * 12
            + graph * 10
            + new_w * 6
            + device * 8
            + hri * 8
            - min(age, 1.0) * 4
        )
        score = float(np.clip(score + rng.normal(0, 4), 0, 100))
        X.append(row)
        y.append(score)
    return np.array(X, dtype=float), np.array(y, dtype=float)


def _load_demo_rows() -> tuple[np.ndarray, np.ndarray]:
    path = _DATA_DIR / "alerts.json"
    if not path.exists():
        return np.zeros((0, len(FEATURE_NAMES))), np.zeros((0,))
    try:
        alerts = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return np.zeros((0, len(FEATURE_NAMES))), np.zeros((0,))
    X, y = [], []
    for a in alerts:
        if not isinstance(a, dict):
            continue
        X.append(vectorize(a)[0])
        y.append(_label_from_alert(a))
    if not X:
        return np.zeros((0, len(FEATURE_NAMES))), np.zeros((0,))
    return np.array(X, dtype=float), np.array(y, dtype=float)


def train_model(*, persist: bool = True) -> dict[str, Any]:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error
    from sklearn.model_selection import train_test_split

    Xs, ys = _synthetic_rows()
    Xd, yd = _load_demo_rows()
    if len(Xd):
        X = np.vstack([Xs, Xd])
        y = np.concatenate([ys, yd])
    else:
        X, y = Xs, ys

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    model = GradientBoostingRegressor(
        n_estimators=80,
        max_depth=3,
        learning_rate=0.08,
        random_state=42,
    )
    model.fit(Xtr, ytr)
    mae = float(mean_absolute_error(yte, model.predict(Xte)))

    global _model, _model_meta
    _model = model
    _model_meta = {
        "model_name": "lowtrans-sklearn-gb-v1",
        "mae": round(mae, 2),
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "features": FEATURE_NAMES,
    }

    if persist:
        _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        import joblib

        joblib.dump({"model": model, "meta": _model_meta}, _MODEL_PATH)

    return _model_meta


def get_model():
    global _model, _model_meta
    if _model is not None:
        return _model, _model_meta
    if _MODEL_PATH.exists():
        try:
            import joblib

            blob = joblib.load(_MODEL_PATH)
            _model = blob["model"]
            _model_meta = blob.get("meta") or {}
            return _model, _model_meta
        except Exception:
            pass
    train_model(persist=True)
    return _model, _model_meta


def predict_sklearn(alert: dict[str, Any]) -> dict[str, Any] | None:
    """Score with GB regressor + importance×value attribution. None if sklearn fails."""
    try:
        model, meta = get_model()
        feats = raw_feature_dict(alert)
        x = vectorize(alert)
        pred = float(model.predict(x)[0])
        score = int(round(max(0.0, min(100.0, pred))))

        importances = getattr(model, "feature_importances_", None)
        attribution = []
        if importances is not None:
            for name, imp in zip(FEATURE_NAMES, importances):
                val = feats[name]
                # contribution proxy: importance * activated magnitude * 100 scale
                contrib = round(float(imp) * float(val) * 40.0, 2)
                if contrib > 0.05:
                    attribution.append({"feature": name, "contribution": contrib, "importance": round(float(imp), 4)})
            attribution.sort(key=lambda a: a["contribution"], reverse=True)

        if score >= 70:
            risk_level = "high"
        elif score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "model": meta.get("model_name", "lowtrans-sklearn-gb-v1"),
            "backend": "sklearn",
            "mae": meta.get("mae"),
            "score": score,
            "risk_level": risk_level,
            "features": feats,
            "attribution": attribution,
            "top_drivers": [a["feature"] for a in attribution[:3]],
            "summary": (
                f"Sklearn GB score {score}/100 ({risk_level})"
                + (f", MAE≈{meta.get('mae')}" if meta.get("mae") is not None else "")
                + (
                    ". Top drivers: "
                    + ", ".join(f"{a['feature']} (+{a['contribution']})" for a in attribution[:3])
                    if attribution
                    else "."
                )
            ),
        }
    except Exception:
        return None
