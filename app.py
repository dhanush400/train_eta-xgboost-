"""Flask web interface for the trained train-delay model (RailPulse AI).

Pages
  /            ETA Dashboard      - single prediction with gauge, range and route progress
  /forecast    Delay Forecast     - stop-by-stop delay forecast + what-if scenarios
  /evaluation  Model Evaluation   - metrics, baselines, importance, residuals, scatter
"""
from pathlib import Path
from datetime import datetime, timedelta
import json
import joblib
import pandas as pd
from flask import Flask, render_template, request, jsonify

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "xgboost_model.pkl"
METRICS_PATH = ROOT / "models" / "metrics.json"

app = Flask(__name__)

FEATURES = [
    "distance_km", "scheduled_hour", "day_of_week", "month",
    "remaining_stops", "previous_delay_min", "weather_severity",
    "congestion_index", "train_type_code",
]
TYPE_NAMES = ["Express", "Superfast", "Passenger", "Rajdhani", "Other"]
WEATHER_NAMES = ["Normal", "Mild", "Moderate", "Severe"]
AVG_SPEED_KMPH = 55.0

_model = None


def ensure_model():
    """Load the model; if it has not been trained yet (e.g. first start on Render) train it."""
    global _model
    if _model is not None:
        return _model
    if not MODEL_PATH.exists():
        try:
            if not (ROOT / "dataset" / "train_data.csv").exists():
                import generate_dataset
                generate_dataset.main()
            import train_model
            train_model.main()
        except Exception as exc:  # pragma: no cover
            print("Auto-training failed:", exc)
            return None
    _model = joblib.load(MODEL_PATH)
    return _model


def load_metrics():
    if METRICS_PATH.exists():
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    return None


def status_for(delay):
    if delay <= 5:
        return "On Time", "ok"
    if delay <= 30:
        return "Slightly Delayed", "warn"
    return "Highly Delayed", "bad"


def parse_form(form):
    train_number = (form.get("train_number") or "").strip()
    scheduled = datetime.strptime(form["scheduled_arrival"], "%Y-%m-%dT%H:%M")
    values = {
        "distance_km": float(form["distance_km"]),
        "scheduled_hour": scheduled.hour,
        "day_of_week": scheduled.weekday(),
        "month": scheduled.month,
        "remaining_stops": int(form["remaining_stops"]),
        "previous_delay_min": float(form["previous_delay_min"]),
        "weather_severity": int(form["weather_severity"]),
        "congestion_index": int(form["congestion_index"]),
        "train_type_code": int(form["train_type_code"]),
    }
    if not train_number:
        raise ValueError("Enter a train number.")
    if values["distance_km"] < 0 or values["remaining_stops"] < 0:
        raise ValueError("Distance and remaining stops cannot be negative.")
    if values["previous_delay_min"] < 0:
        raise ValueError("Previous delay cannot be negative.")
    if not 0 <= values["weather_severity"] <= 3:
        raise ValueError("Weather severity must be between 0 and 3.")
    if not 0 <= values["congestion_index"] <= 10:
        raise ValueError("Congestion index must be between 0 and 10.")
    if not 0 <= values["train_type_code"] <= 4:
        raise ValueError("Select a valid train type.")
    return train_number, scheduled, values


def predict_delay(model, values):
    df = pd.DataFrame([[values[c] for c in FEATURES]], columns=FEATURES)
    return max(0.0, float(model.predict(df)[0]))


def simulate_journey(model, scheduled, values, weather=None, congestion=None):
    """Roll the model forward stop by stop; each stop's predicted delay becomes
    the 'previous station delay' of the next stop."""
    v = dict(values)
    if weather is not None:
        v["weather_severity"] = weather
    if congestion is not None:
        v["congestion_index"] = congestion
    total_stops = max(v["remaining_stops"], 1)
    total_dist = v["distance_km"]
    prev = v["previous_delay_min"]
    stops = [{"stop": 0, "label": "Now", "delay": round(prev, 1),
              "time": (scheduled - timedelta(hours=total_dist / AVG_SPEED_KMPH)).strftime("%I:%M %p")}]
    for i in range(1, total_stops + 1):
        left = total_stops - i
        dist_left = total_dist * left / total_stops
        sched_i = scheduled - timedelta(hours=dist_left / AVG_SPEED_KMPH)
        step = dict(v)
        step.update({
            "distance_km": dist_left,
            "remaining_stops": left,
            "previous_delay_min": prev,
            "scheduled_hour": sched_i.hour,
            "day_of_week": sched_i.weekday(),
            "month": sched_i.month,
        })
        d = predict_delay(model, step)
        prev = d
        stops.append({
            "stop": i,
            "label": "Destination" if i == total_stops else f"Stop {i}",
            "delay": round(d, 1),
            "time": (sched_i + timedelta(minutes=d)).strftime("%I:%M %p"),
            "sched": sched_i.strftime("%I:%M %p"),
            "status": status_for(d)[0],
            "tone": status_for(d)[1],
        })
    return stops


@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    error = None
    metrics = load_metrics()
    forecast_args = {}

    if request.method == "POST":
        model = ensure_model()
        if model is None:
            error = "Model file not found. Run generate_dataset.py and train_model.py first."
        else:
            try:
                train_number, scheduled, values = parse_form(request.form)
                predicted_delay = predict_delay(model, values)
                predicted_eta = scheduled + timedelta(minutes=predicted_delay)
                status, tone = status_for(predicted_delay)
                half = (metrics or {}).get("interval90_minutes", 5.0)
                result = {
                    "train_number": train_number,
                    "delay": round(predicted_delay, 1),
                    "scheduled_eta": scheduled.strftime("%d-%m-%Y %I:%M %p"),
                    "predicted_eta": predicted_eta.strftime("%d-%m-%Y %I:%M %p"),
                    "status": status,
                    "tone": tone,
                    "low": round(max(0.0, predicted_delay - half), 1),
                    "high": round(predicted_delay + half, 1),
                    "stops": min(values["remaining_stops"], 8),
                    "remaining": values["remaining_stops"],
                    "distance": round(values["distance_km"]),
                    "weather": WEATHER_NAMES[values["weather_severity"]],
                    "category": TYPE_NAMES[values["train_type_code"]],
                    "congestion": values["congestion_index"],
                }
                forecast_args = {k: request.form.get(k, "") for k in [
                    "train_number", "scheduled_arrival", "distance_km", "remaining_stops",
                    "previous_delay_min", "weather_severity", "congestion_index", "train_type_code"]}
            except (ValueError, KeyError) as exc:
                error = str(exc)

    return render_template("index.html", result=result, error=error, metrics=metrics,
                           forecast_args=forecast_args, page="home")


@app.route("/forecast")
def forecast():
    return render_template("forecast.html", metrics=load_metrics(), page="forecast")


@app.route("/api/forecast", methods=["POST"])
def api_forecast():
    model = ensure_model()
    if model is None:
        return jsonify({"error": "Model not available. Run train_model.py first."}), 500
    try:
        train_number, scheduled, values = parse_form(request.form)
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400

    stops = simulate_journey(model, scheduled, values)
    final = stops[-1]
    final_eta = scheduled + timedelta(minutes=final["delay"])
    peak = max(stops[1:], key=lambda s: s["delay"]) if len(stops) > 1 else final

    whatif_weather = [
        {"label": name, "value": round(simulate_journey(model, scheduled, values, weather=i)[-1]["delay"], 1)}
        for i, name in enumerate(WEATHER_NAMES)
    ]
    whatif_congestion = [
        {"label": f"Index {c}", "value": round(simulate_journey(model, scheduled, values, congestion=c)[-1]["delay"], 1)}
        for c in (0, 3, 6, 10)
    ]
    return jsonify({
        "train_number": train_number,
        "stops": stops,
        "final_delay": final["delay"],
        "final_eta": final_eta.strftime("%d-%m-%Y %I:%M %p"),
        "scheduled": scheduled.strftime("%d-%m-%Y %I:%M %p"),
        "peak_delay": peak["delay"],
        "peak_label": peak["label"],
        "delayed_stops": sum(1 for s in stops[1:] if s["delay"] > 5),
        "trend": "growing" if final["delay"] > stops[0]["delay"] + 1 else ("recovering" if final["delay"] < stops[0]["delay"] - 1 else "steady"),
        "whatif_weather": whatif_weather,
        "whatif_congestion": whatif_congestion,
    })


@app.route("/evaluation")
def evaluation():
    return render_template("evaluation.html", metrics=load_metrics(), page="evaluation")


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
