import pandas as pd
import joblib

def preprocess_deploy(df, model_path):
    """
    Transform the full dataset using saved scaler and encoders from training.
    Returns:
        X_scaled : DataFrame with scaled features (includes event_id column)
        target_encoder : the saved target encoder (for decoding predictions)
    """
    # Load saved artifacts
    saved = joblib.load(model_path)
    scaler = saved["scaler"]
    encoders = saved["encoders"]
    feature_cols = saved["feature_cols"]
    target_encoder = saved.get("target_encoder", None)

    data = df.copy()

    # ── Time features (same as training) ──
    if "logged" in data.columns:
        data["logged"] = pd.to_datetime(data["logged"], errors="coerce")
        data["hour"] = data["logged"].dt.hour.fillna(0).astype(int)
        data["day_of_week"] = data["logged"].dt.dayofweek.fillna(0).astype(int)
        data["is_weekend"] = (data["day_of_week"] >= 5).astype(int)
    else:
        data["hour"] = 0
        data["day_of_week"] = 0
        data["is_weekend"] = 0

    # ── Drop non‑feature columns ──
    drop_cols = ["id", "logged", "status", "assigned_to"]
    data.drop(columns=[c for c in drop_cols if c in data.columns], inplace=True, errors="ignore")

    # ── Ensure event_id exists ──
    if "event_id" not in data.columns:
        data["event_id"] = data.index.astype(str)

    # ── Apply saved encoders (handle unseen categories gracefully) ──
    for col in feature_cols:
        if col in encoders:
            le = encoders[col]
            # Replace unseen values with the first known class (or most frequent)
            known_classes = set(le.classes_)
            # Use .apply to map unknown to the first class
            def map_value(x):
                x_str = str(x)
                if x_str in known_classes:
                    return x_str
                else:
                    return le.classes_[0]
            data[col] = data[col].apply(map_value)
            data[col] = le.transform(data[col].astype(str))

    # ── Scale using saved scaler ──
    X = data[feature_cols].copy()
    X_scaled = scaler.transform(X)
    X_scaled_df = pd.DataFrame(X_scaled, columns=feature_cols, index=X.index)
    X_scaled_df["event_id"] = data["event_id"].values

    return X_scaled_df, target_encoder