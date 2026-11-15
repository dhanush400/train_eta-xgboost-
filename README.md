# AI-Based Dynamic Train ETA Prediction and Delay Forecasting Using XGBoost

## Important dataset note
The included starter workflow generates a **simulated dataset** (`dataset/train_data.csv`) so the complete application can be demonstrated without waiting for an external dataset. It is not official Indian Railways data and must not be presented as real operational evidence. For research claims, replace it with verified historical train movement records and document the source, date range, missing-value treatment, and train/station coverage.

## Requirements
- Python 3.10+
- VS Code (recommended)

## Setup on Windows
Open this folder in VS Code. Open Terminal > New Terminal, then run:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

If `python` is not recognized, try `py` instead.

## Run the implementation
Run these commands in order:

```powershell
python generate_dataset.py
python train_model.py
python app.py
```

Open this address in your browser:

`http://127.0.0.1:5000`

## Project files
- `generate_dataset.py`: creates 5,000 simulated sample records.
- `dataset/train_data.csv`: generated training dataset (created by the first command).
- `train_model.py`: trains XGBoost, evaluates MAE/RMSE/R², saves the model and an actual-vs-predicted graph.
- `models/xgboost_model.pkl`: trained model (created by the second command).
- `models/metrics.json`: evaluation metrics (created by the second command).
- `app.py`: Flask server and ETA calculation.
- `templates/index.html`, `forecast.html`, `evaluation.html` (+ `base.html`, `_fields.html`): the three working pages - ETA Dashboard, Delay Forecast (stop-by-stop + what-if), Model Evaluation (baselines, importance, residuals).
- `static/style.css`, `static/charts.js`: styling (light/dark mode) and dependency-free charts.
- `static/actual_vs_predicted.png`: evaluation graph.

## Model inputs
`distance_km`, `scheduled_hour`, `day_of_week`, `month`, `remaining_stops`, `previous_delay_min`, `weather_severity`, `congestion_index`, `train_type_code`.

Target: `delay_minutes`.

The model estimates delay in minutes. The application adds predicted delay to the user-entered scheduled arrival timestamp to calculate predicted ETA.

## For the project guide
Demonstrate dataset generation, model training, printed evaluation metrics, saved model, Flask web page, and a prediction using changed input values. Explain that the included data is simulated. Do not describe the prototype as live train tracking: live operation requires a verified real-time railway data source and an updated prediction pipeline.

## Troubleshooting
- `ModuleNotFoundError`: activate the virtual environment and run `pip install -r requirements.txt`.
- `FileNotFoundError` for dataset: run `python generate_dataset.py` first.
- Model file not found in website: run `python train_model.py` before `python app.py`.
- Port 5000 busy: change `port=5000` in `app.py` to `port=5001`, then open `http://127.0.0.1:5001`.


## Deploying on Render
Build command: `pip install -r requirements.txt`  |  Start command: `gunicorn app:app`.
If `models/` is not in the repo, the app trains the model automatically on first use (takes a few seconds). Health check path: `/healthz`.
