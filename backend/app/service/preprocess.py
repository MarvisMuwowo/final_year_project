import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings("ignore")

# Feature columns used by all models
FEATURE_COLS = [
    "event_id",
    "level",
    "user",
    "log_name",
    "opcode",
    "computer",
    "keyword",
    "hour",
    "day_of_week",
    "is_weekend",
]

def process_data(df):
    """
    Preprocess for training: split data first, then fit encoders and scaler on training set only.
    Returns:
        X_train, X_test, y_train, y_test, encoders, scaler
    """
    data = df.copy()
    target_col = "task_category"

    if target_col not in data.columns:
        raise ValueError(f"Missing target column: {target_col}")

    # ── Time features ──
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

    # ── Merge rare target classes ──
    counts = data[target_col].value_counts()
    rare = counts[counts < 5].index.tolist()
    if rare:
        data[target_col] = data[target_col].replace(rare, "Other")

    # ── Check required features ──
    missing = [c for c in FEATURE_COLS if c not in data.columns]
    if missing:
        raise ValueError(f"Missing required feature columns: {missing}")

    X = data[FEATURE_COLS].copy()
    y = data[target_col].copy()

    # ── Split train/test FIRST ──
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # ── Encode categorical features on training set only ──
    encoders = {}
    for col in FEATURE_COLS:
        if not is_numeric_dtype(X_train_raw[col]):
            le = LabelEncoder()
            X_train_raw[col] = le.fit_transform(X_train_raw[col].astype(str))
            # Transform test set with same encoder
            X_test_raw[col] = le.transform(X_test_raw[col].astype(str))
            encoders[col] = le
        else:
            # Numeric columns: already numeric, no encoding needed
            pass

    # ── Scale on training set only ──
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_raw)
    X_test_scaled = scaler.transform(X_test_raw)

    X_train = pd.DataFrame(X_train_scaled, columns=FEATURE_COLS, index=X_train_raw.index)
    X_test = pd.DataFrame(X_test_scaled, columns=FEATURE_COLS, index=X_test_raw.index)

    print("\n── Class Distribution ──")
    print(y.value_counts())
    print(f"\nTraining samples : {len(X_train)}")
    print(f"Testing samples  : {len(X_test)}")

    return X_train, X_test, y_train, y_test, encoders, scaler