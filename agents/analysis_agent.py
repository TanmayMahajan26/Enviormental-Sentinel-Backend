"""
🔵 ANALYSIS AGENT — ML Brain
The core machine learning pipeline for the Environmental Sentinel.

Pipeline:
1. STL Decomposition — Strips seasonal patterns to get residuals
2. Feature Engineering — Rolling stats, rate-of-change, lag features
3. Isolation Forest — Trained on residuals (per zone, multivariate)
4. Holt-Winters Forecasting — Probabilistic predictions with confidence intervals

This agent TRAINS real ML models on 90 days of data and saves them.
Models are then used for inference on new/recent data.
"""
import numpy as np
import pandas as pd
import os
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import warnings

from config import (
    ISOLATION_FOREST_CONTAMINATION,
    ISOLATION_FOREST_N_ESTIMATORS,
    STL_PERIOD,
    ROLLING_WINDOW,
    FORECAST_HORIZON_HOURS,
    MODELS_DIR,
)
import database as db

warnings.filterwarnings("ignore")

SIGNALS = ["sst", "chlorophyll", "wind_speed", "ph", "turbidity"]


def ensure_models_dir():
    os.makedirs(MODELS_DIR, exist_ok=True)


def _stl_decompose(series: pd.Series, period: int = STL_PERIOD) -> dict:
    """
    Apply STL decomposition to extract trend, seasonal, and residual.
    Returns dict with all three components.
    """
    try:
        stl = STL(series, period=period, robust=True)
        result = stl.fit()
        return {
            "trend": result.trend,
            "seasonal": result.seasonal,
            "residual": result.resid,
        }
    except Exception as e:
        print(f"    [Analysis] STL failed: {e}, using simple detrending")
        # Fallback: simple rolling mean subtraction
        trend = series.rolling(window=period, center=True, min_periods=1).mean()
        residual = series - trend
        seasonal = pd.Series(np.zeros(len(series)), index=series.index)
        return {"trend": trend, "seasonal": seasonal, "residual": residual}


def _engineer_features(df: pd.DataFrame, residuals: dict) -> pd.DataFrame:
    """
    Create ML features from residuals and raw data.

    Features per signal:
    - residual value
    - rolling mean of residual (12h window)
    - rolling std of residual (12h window)
    - rate of change (first derivative)
    - lag features (t-1, t-6, t-12)
    - z-score of residual
    """
    features = pd.DataFrame(index=df.index)

    for signal in SIGNALS:
        resid = residuals[signal]

        # Residual value
        features[f"{signal}_residual"] = resid.values

        # Rolling statistics
        features[f"{signal}_roll_mean"] = resid.rolling(
            window=ROLLING_WINDOW, min_periods=1
        ).mean().values
        features[f"{signal}_roll_std"] = resid.rolling(
            window=ROLLING_WINDOW, min_periods=1
        ).std().fillna(0).values

        # Rate of change
        features[f"{signal}_roc"] = resid.diff().fillna(0).values

        # Lag features
        features[f"{signal}_lag1"] = resid.shift(1).fillna(0).values
        features[f"{signal}_lag6"] = resid.shift(6).fillna(0).values
        features[f"{signal}_lag12"] = resid.shift(12).fillna(0).values

        # Z-score
        mean = resid.mean()
        std = resid.std()
        if std > 0:
            features[f"{signal}_zscore"] = ((resid - mean) / std).values
        else:
            features[f"{signal}_zscore"] = np.zeros(len(resid))

    # Fill any remaining NaN
    features = features.fillna(0)
    return features


def train_zone_model(zone_id: str) -> dict:
    """
    Train Isolation Forest + forecasting models for a single zone.

    Returns:
        dict with training results (anomaly count, model metrics)
    """
    ensure_models_dir()
    print(f"  [Analysis Agent] Training models for {zone_id}...")

    # Load all readings for this zone
    readings = db.get_all_readings_for_zone(zone_id)
    if not readings:
        print(f"    No data for {zone_id}, skipping.")
        return {"zone_id": zone_id, "status": "no_data"}

    df = pd.DataFrame(readings)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # ═══════════════════════════════════════════
    # STEP 1: STL Decomposition per signal
    # ═══════════════════════════════════════════
    residuals = {}
    decompositions = {}

    for signal in SIGNALS:
        series = df[signal].astype(float)
        series.index = pd.RangeIndex(len(series))

        decomp = _stl_decompose(series)
        residuals[signal] = decomp["residual"]
        decompositions[signal] = decomp

    print(f"    ✓ STL decomposition complete (5 signals)")

    # ═══════════════════════════════════════════
    # STEP 2: Feature Engineering
    # ═══════════════════════════════════════════
    feature_df = _engineer_features(df, residuals)

    # Scale features
    scaler = StandardScaler()
    X = scaler.fit_transform(feature_df.values)

    print(f"    ✓ Feature engineering complete ({X.shape[1]} features)")

    # ═══════════════════════════════════════════
    # STEP 3: Train Isolation Forest
    # ═══════════════════════════════════════════
    iso_forest = IsolationForest(
        n_estimators=ISOLATION_FOREST_N_ESTIMATORS,
        contamination=ISOLATION_FOREST_CONTAMINATION,
        max_samples="auto",
        random_state=42,
        n_jobs=-1,
    )

    iso_forest.fit(X)

    # Get anomaly scores and predictions
    scores = iso_forest.decision_function(X)     # higher = more normal
    predictions = iso_forest.predict(X)           # 1=normal, -1=anomaly

    anomaly_mask = predictions == -1
    anomaly_count = anomaly_mask.sum()
    print(f"    ✓ Isolation Forest trained — {anomaly_count} anomalies detected ({anomaly_count / len(X) * 100:.1f}%)")

    # ═══════════════════════════════════════════
    # STEP 4: Train Forecasting Models (Holt-Winters)
    # ═══════════════════════════════════════════
    forecast_models = {}

    for signal in ["sst", "chlorophyll"]:  # forecast key signals
        try:
            series = df[signal].astype(float).values
            # Use last 720 points (30 days) for forecast model to keep it fast
            train_series = series[-720:]

            hw_model = ExponentialSmoothing(
                train_series,
                seasonal_periods=24,
                trend="add",
                seasonal="add",
                use_boxcox=False,
            ).fit(optimized=True)

            forecast_models[signal] = hw_model
            print(f"    ✓ Holt-Winters forecast model trained for {signal}")
        except Exception as e:
            print(f"    ⚠ Forecast model failed for {signal}: {e}")

    # ═══════════════════════════════════════════
    # STEP 5: Save Models
    # ═══════════════════════════════════════════
    model_data = {
        "iso_forest": iso_forest,
        "scaler": scaler,
        "feature_columns": list(feature_df.columns),
        "forecast_models": forecast_models,
        "signal_stats": {
            signal: {
                "mean": float(residuals[signal].mean()),
                "std": float(residuals[signal].std()),
                "baseline_mean": float(df[signal].mean()),
                "baseline_std": float(df[signal].std()),
            }
            for signal in SIGNALS
        },
    }

    model_path = os.path.join(MODELS_DIR, f"{zone_id}_model.pkl")
    joblib.dump(model_data, model_path)
    print(f"    ✓ Models saved to {model_path}")

    # ═══════════════════════════════════════════
    # STEP 6: Store Detected Anomalies in DB
    # ═══════════════════════════════════════════
    anomaly_records = []

    for idx in np.where(anomaly_mask)[0]:
        # Find which signal contributed most to this anomaly
        worst_signal = None
        worst_zscore = 0

        for signal in SIGNALS:
            z = abs(feature_df.iloc[idx][f"{signal}_zscore"])
            if z > worst_zscore:
                worst_zscore = z
                worst_signal = signal

        if worst_signal:
            expected = float(df[worst_signal].mean())
            actual = float(df.iloc[idx][worst_signal])
            deviation = abs(actual - expected) / max(abs(expected), 0.001) * 100

            anomaly_records.append({
                "zone_id": zone_id,
                "timestamp": df.iloc[idx]["timestamp"].isoformat(),
                "signal": worst_signal,
                "anomaly_score": float(scores[idx]),
                "z_score": float(worst_zscore),
                "value": actual,
                "expected_value": expected,
                "deviation_pct": round(deviation, 2),
            })

    if anomaly_records:
        db.insert_anomalies_batch(anomaly_records)
        print(f"    ✓ Stored {len(anomaly_records)} anomaly records in database")

    return {
        "zone_id": zone_id,
        "status": "trained",
        "total_points": len(X),
        "features": X.shape[1],
        "anomalies_detected": anomaly_count,
        "anomaly_rate": round(anomaly_count / len(X) * 100, 2),
    }


def train_all_zones() -> list[dict]:
    """Train models for all zones. Returns training results."""
    zones = db.get_all_zones()
    results = []

    print("\n[Analysis Agent] 🧠 Training ML models on 90-day India dataset...")
    print("=" * 60)

    for zone in zones:
        result = train_zone_model(zone["id"])
        results.append(result)

    print("=" * 60)
    total_anomalies = sum(r.get("anomalies_detected", 0) for r in results)
    print(f"[Analysis Agent] ✅ Training complete. Total anomalies: {total_anomalies}")
    return results


def get_forecast(zone_id: str, signal: str = "sst",
                 horizon: int = FORECAST_HORIZON_HOURS) -> list[dict]:
    """
    Generate probabilistic forecast for a zone-signal pair.
    Returns list of {timestamp, predicted_value, lower_bound, upper_bound}.
    """
    model_path = os.path.join(MODELS_DIR, f"{zone_id}_model.pkl")
    if not os.path.exists(model_path):
        return []

    model_data = joblib.load(model_path)
    forecast_models = model_data.get("forecast_models", {})

    if signal not in forecast_models:
        return []

    hw_model = forecast_models[signal]

    try:
        # Generate forecast
        forecast = hw_model.forecast(steps=horizon)

        # Estimate confidence intervals using residual std
        stats = model_data["signal_stats"][signal]
        residual_std = stats["std"]

        # 95% CI = ±1.96 * residual_std (grows slightly over time)
        ci_growth = np.sqrt(np.arange(1, horizon + 1) / 24)  # uncertainty grows
        ci = 1.96 * residual_std * ci_growth

        # Get the last timestamp from readings
        readings = db.get_all_readings_for_zone(zone_id)
        if readings:
            last_ts = pd.to_datetime(readings[-1]["timestamp"])
        else:
            last_ts = pd.Timestamp.now()

        result = []
        for i in range(horizon):
            ts = last_ts + pd.Timedelta(hours=i + 1)
            result.append({
                "timestamp": ts.isoformat(),
                "predicted_value": round(float(forecast.iloc[i]), 3),
                "lower_bound": round(float(forecast.iloc[i] - ci[i]), 3),
                "upper_bound": round(float(forecast.iloc[i] + ci[i]), 3),
            })

        return result

    except Exception as e:
        print(f"[Analysis] Forecast error for {zone_id}/{signal}: {e}")
        return []


def analyze_recent(zone_id: str, n_recent: int = 24) -> list[dict]:
    """
    Run anomaly detection on the most recent N readings.
    Uses the trained model for the zone.
    """
    model_path = os.path.join(MODELS_DIR, f"{zone_id}_model.pkl")
    if not os.path.exists(model_path):
        return []

    model_data = joblib.load(model_path)
    iso_forest = model_data["iso_forest"]
    scaler = model_data["scaler"]

    # Get recent readings
    readings = db.get_all_readings_for_zone(zone_id)
    if len(readings) < n_recent + ROLLING_WINDOW:
        return []

    df = pd.DataFrame(readings[-n_recent - ROLLING_WINDOW - 24:])
    for col in SIGNALS:
        df[col] = df[col].astype(float)

    # Decompose recent data
    residuals = {}
    for signal in SIGNALS:
        series = df[signal].astype(float)
        series.index = pd.RangeIndex(len(series))
        decomp = _stl_decompose(series)
        residuals[signal] = decomp["residual"]

    # Engineer features
    feature_df = _engineer_features(df, residuals)

    # Only take the last n_recent rows
    feature_recent = feature_df.iloc[-n_recent:]
    X = scaler.transform(feature_recent.values)

    # Predict
    scores = iso_forest.decision_function(X)
    predictions = iso_forest.predict(X)

    anomalies = []
    for i, (score, pred) in enumerate(zip(scores, predictions)):
        if pred == -1:
            idx = len(df) - n_recent + i
            row = df.iloc[idx]

            # Find worst signal
            worst_signal = None
            worst_z = 0
            for signal in SIGNALS:
                z = abs(feature_recent.iloc[i][f"{signal}_zscore"])
                if z > worst_z:
                    worst_z = z
                    worst_signal = signal

            if worst_signal:
                anomalies.append({
                    "zone_id": zone_id,
                    "timestamp": str(row["timestamp"]),
                    "signal": worst_signal,
                    "anomaly_score": float(score),
                    "z_score": float(worst_z),
                    "value": float(row[worst_signal]),
                    "expected_value": float(model_data["signal_stats"][worst_signal]["baseline_mean"]),
                    "deviation_pct": round(
                        abs(float(row[worst_signal]) - model_data["signal_stats"][worst_signal]["baseline_mean"])
                        / max(abs(model_data["signal_stats"][worst_signal]["baseline_mean"]), 0.001) * 100,
                        2
                    ),
                })

    return anomalies


if __name__ == "__main__":
    results = train_all_zones()
    for r in results:
        print(f"  {r['zone_id']}: {r.get('anomalies_detected', 0)} anomalies")
