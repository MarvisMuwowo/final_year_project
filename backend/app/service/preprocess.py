import numpy as np
import psycopg2
import sys
import os
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'database'))
from config import DB_CONFIG


# ── 1. READ DATA ──────────────────────────────────────────────────────────────
def get_events(conn):
    query = "SELECT * FROM events"
    return pd.read_sql(query, conn)


# ── 2. PROCESS DATA ───────────────────────────────────────────────────────────
def process_data(df):

    print("\n── Raw Data ──")
    print(df.head())
    print(f"Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")

    # Drop duplicates & irrelevant columns
    df = df.drop_duplicates()
    df = df.drop(columns=["id"], errors="ignore")

    # Merge rare task_categories into "Other"
    min_samples  = 30
    class_counts = df["task_category"].value_counts()
    rare_classes = class_counts[class_counts < min_samples].index
    df["task_category"] = df["task_category"].apply(
        lambda x: "Other" if x in rare_classes else x
    )

    print("\n── Class distribution after merging rare classes ──")
    print(df["task_category"].value_counts())

    # Parse datetime & extract features
    df["logged"]      = pd.to_datetime(df["logged"])
    df["hour"]        = df["logged"].dt.hour
    df["day_of_week"] = df["logged"].dt.dayofweek
    df["is_weekend"]  = df["day_of_week"].isin([5, 6]).astype(int)
    df = df.drop(columns=["logged"])

    # Encode categorical columns
    le               = LabelEncoder()
    categorical_cols = ["level", "user", "log_name", "opcode", "computer", "keyword"]
    for col in categorical_cols:
        df[col] = le.fit_transform(df[col].astype(str))

    # Feature / target split
    X = df.drop(columns=["task_category"])
    y = df["task_category"]

    label = LabelEncoder()
    y     = label.fit_transform(y)

    print("\nClassification distribution")
    print("Total samples:", len(y))
    print("Classes found:", label.classes_)
    print("Class count:", dict(zip(*np.unique(y, return_counts=True))))

    # Train / test split FIRST
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Scale AFTER splitting
    scaler         = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)

    X_train = pd.DataFrame(X_train_scaled, columns=X_train.columns)
    X_test  = pd.DataFrame(X_test_scaled,  columns=X_test.columns)

    print("\n── Processed Data ──")
    print(f"Training samples : {X_train.shape[0]}")
    print(f"Testing  samples : {X_test.shape[0]}")
    print(f"Features         : {X_train.columns.tolist()}")

    return X_train, X_test, y_train, y_test


# ── 3. RUN ONLY WHEN EXECUTED DIRECTLY ───────────────────────────────────────
if __name__ == "__main__":
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Connected successfully")
    except Exception as e:
        print("Connection failed:", e)
        conn = None

    if conn:
        df = get_events(conn)
        X_train, X_test, y_train, y_test = process_data(df)
        conn.close()
        print("\nConnection closed")
        print("\nData is ready for ML training ✓")