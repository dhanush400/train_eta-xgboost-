"""Generate a SIMULATED starter dataset for the Train ETA project.

Replace this dataset with verified historical railway records before making
real-world accuracy claims. The synthetic data is only for demonstrating
the end-to-end implementation.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "dataset" / "train_data.csv"

def main():
    rng = np.random.default_rng(42)
    n = 5000

    df = pd.DataFrame({
        "distance_km": rng.integers(20, 1501, n),
        "scheduled_hour": rng.integers(0, 24, n),
        "day_of_week": rng.integers(0, 7, n),
        "month": rng.integers(1, 13, n),
        "remaining_stops": rng.integers(1, 21, n),
        "previous_delay_min": rng.integers(0, 91, n),
        "weather_severity": rng.integers(0, 4, n),
        "congestion_index": rng.integers(0, 11, n),
        "train_type_code": rng.integers(0, 5, n),
    })

    noise = rng.normal(0, 5, n)
    delay = (
        0.008 * df["distance_km"]
        + 0.45 * df["previous_delay_min"]
        + 0.8 * df["remaining_stops"]
        + 3.0 * df["weather_severity"]
        + 1.5 * df["congestion_index"]
        + 1.2 * df["train_type_code"]
        + noise
    )
    df["delay_minutes"] = np.clip(delay, 0, None).round(2)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Created {OUT}")
    print(f"Rows: {len(df)}")
    print(df.head().to_string(index=False))

if __name__ == "__main__":
    main()
