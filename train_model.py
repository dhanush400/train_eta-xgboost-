"""Train and evaluate an XGBoost regression model for delay prediction.

Besides MAE / RMSE / R2 this script now also writes everything the
"Model Evaluation" page needs (baselines, feature importance, residuals,
actual-vs-predicted sample, per-train-type error) into models/metrics.json.
"""
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    from xgboost import XGBRegressor
    MODEL_NAME = "XGBoost"

    def build_model():
        return XGBRegressor(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            subsample=0.9, colsample_bytree=0.9,
            objective="reg:squarederror", random_state=42, n_jobs=-1,
        )
except ImportError:  # keeps the project runnable even if xgboost failed to install
    from sklearn.ensemble import GradientBoostingRegressor
    MODEL_NAME = "Gradient Boosting (xgboost not installed)"

    def build_model():
        return GradientBoostingRegressor(
            n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.9, random_state=42
        )

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "dataset" / "train_data.csv"
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / "xgboost_model.pkl"
METRICS_PATH = MODEL_DIR / "metrics.json"
PLOT_PATH = ROOT / "static" / "actual_vs_predicted.png"

FEATURES = [
    "distance_km", "scheduled_hour", "day_of_week", "month",
    "remaining_stops", "previous_delay_min", "weather_severity",
    "congestion_index", "train_type_code",
]
FEATURE_LABELS = {
    "distance_km": "Distance to destination",
    "scheduled_hour": "Scheduled hour",
    "day_of_week": "Day of week",
    "month": "Month",
    "remaining_stops": "Remaining stops",
    "previous_delay_min": "Previous station delay",
    "weather_severity": "Weather severity",
    "congestion_index": "Congestion index",
    "train_type_code": "Train category",
}
TYPE_NAMES = ["Express", "Superfast", "Passenger", "Rajdhani", "Other"]
TARGET = "delay_minutes"


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run 'python generate_dataset.py' first."
        )

    df = pd.read_csv(DATA_PATH)
    required = FEATURES + [TARGET]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing columns: {missing}")

    df = df[required].dropna()
    X, y = df[FEATURES], df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    model = build_model()
    model.fit(X_train, y_train)

    predictions = np.clip(model.predict(X_test), 0, None)
    residuals = predictions - y_test.values
    mae = float(mean_absolute_error(y_test, predictions))
    rmse = float(mean_squared_error(y_test, predictions) ** 0.5)
    r2 = float(r2_score(y_test, predictions))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "static").mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    # ---- baselines (what the model has to beat) ----
    baselines = [
        {"name": "Timetable (assume no delay)", "mae": float(np.mean(np.abs(y_test.values)))},
        {"name": "Average delay", "mae": float(np.mean(np.abs(y_test.values - y_train.mean())))},
        {"name": "Carry previous delay", "mae": float(np.mean(np.abs(y_test.values - X_test["previous_delay_min"].values)))},
        {"name": MODEL_NAME.split(" (")[0], "mae": mae},
    ]

    # ---- feature importance ----
    imp = np.asarray(model.feature_importances_, dtype=float)
    imp = imp / imp.sum() * 100
    importance = sorted(
        ({"feature": FEATURE_LABELS[f], "importance": round(float(v), 2)} for f, v in zip(FEATURES, imp)),
        key=lambda d: d["importance"], reverse=True,
    )

    # ---- residual histogram ----
    counts, edges = np.histogram(residuals, bins=24)
    # ---- actual vs predicted sample ----
    rng = np.random.default_rng(1)
    idx = rng.choice(len(y_test), size=min(450, len(y_test)), replace=False)
    scatter = [[round(float(y_test.values[i]), 2), round(float(predictions[i]), 2)] for i in idx]

    # ---- error by train category ----
    by_type = []
    for code, name in enumerate(TYPE_NAMES):
        m = (X_test["train_type_code"].values == code)
        if m.any():
            by_type.append({"type": name, "mae": round(float(np.mean(np.abs(residuals[m]))), 2), "n": int(m.sum())})

    abs_res = np.abs(residuals)
    metrics = {
        "model_name": MODEL_NAME,
        "mae_minutes": round(mae, 3),
        "rmse_minutes": round(rmse, 3),
        "r2_score": round(r2, 4),
        "within_5_min_pct": round(float(np.mean(abs_res <= 5) * 100), 1),
        "within_10_min_pct": round(float(np.mean(abs_res <= 10) * 100), 1),
        "interval90_minutes": round(float(np.quantile(abs_res, 0.90)), 2),
        "test_rows": int(len(y_test)),
        "train_rows": int(len(y_train)),
        "dataset_rows": int(len(df)),
        "dataset_type": "simulated starter dataset" if "SIMULATED" in (ROOT / "README.md").read_text(encoding="utf-8") else "check dataset provenance",
        "baselines": [{"name": b["name"], "mae": round(b["mae"], 3)} for b in baselines],
        "feature_importance": importance,
        "residual_hist": {"counts": counts.tolist(), "edges": [round(float(e), 2) for e in edges]},
        "scatter": scatter,
        "by_type": by_type,
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    plt.figure(figsize=(7, 5))
    plt.scatter(y_test, predictions, alpha=0.5)
    low = min(float(y_test.min()), float(predictions.min()))
    high = max(float(y_test.max()), float(predictions.max()))
    plt.plot([low, high], [low, high], linestyle="--")
    plt.xlabel("Actual delay (minutes)")
    plt.ylabel("Predicted delay (minutes)")
    plt.title("Actual vs Predicted Train Delay")
    plt.tight_layout()
    plt.savefig(PLOT_PATH, dpi=150)
    plt.close()

    print(f"{MODEL_NAME} training completed.")
    print(f"MAE  : {mae:.2f} minutes")
    print(f"RMSE : {rmse:.2f} minutes")
    print(f"R2   : {r2:.4f}")
    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved metrics: {METRICS_PATH}")
    print(f"Saved graph: {PLOT_PATH}")


if __name__ == "__main__":
    main()
