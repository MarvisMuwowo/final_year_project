import pandas as pd
import psycopg2
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight
from imblearn.combine import SMOTETomek
from imblearn.over_sampling import SMOTE
from collections import Counter
import numpy as np
import joblib
import matplotlib.pyplot as plt
import sys
import os

# Replace this
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'service')))
from preprocess import process_data

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'database'))
from config import DB_CONFIG


# ── DB CONNECTION ─────────────────────────────────────────────────────────────
try:
    conn = psycopg2.connect(**DB_CONFIG)
    print("Connected successfully")
except Exception as e:
    print("Connection failed:", e)
    conn = None


# ── READ DATA ─────────────────────────────────────────────────────────────────
def get_events(conn):
    query = "SELECT * FROM events"
    return pd.read_sql(query, conn)


# ── 1. RESAMPLING ─────────────────────────────────────────────────────────────
def apply_resampling(X_train, y_train, random_state=42):
    """
    SMOTETomek with dynamic k_neighbors based on smallest class size.
    """
    print("\n── Class distribution BEFORE resampling ──")
    counts = Counter(y_train)
    print(counts)

    min_samples = min(counts.values())

    if min_samples < 2:
        print("  Too few samples to resample — skipping SMOTE")
        return X_train, y_train

    k = min(5, min_samples - 1)
    print(f"  Using k_neighbors={k} (smallest class has {min_samples} samples)")

    resampler = SMOTETomek(
        smote=SMOTE(k_neighbors=k, random_state=random_state),
        random_state=random_state
    )

    X_res, y_res = resampler.fit_resample(X_train, y_train)

    print("\n── Class distribution AFTER resampling ──")
    print(Counter(y_res))

    return X_res, y_res


# ── 2. TRAIN RANDOM FOREST ────────────────────────────────────────────────────
def train_random_forest(X_train, X_test, y_train, y_test):
    """
    Train a multi-class Random Forest classifier with imbalance-aware techniques:
      - SMOTETomek resampling on the training split
      - class_weight='balanced' as secondary safeguard
    """
    print("\n── Training Random Forest Model ──")

    # Balance training data
    X_train_bal, y_train_bal = apply_resampling(X_train, y_train)

    # Per-sample weights on the balanced set
    sample_weights = compute_sample_weight(
        class_weight="balanced", y=y_train_bal
    )

    model = RandomForestClassifier(
        n_estimators  = 500,        # number of trees
        max_depth     = 8,          # max depth per tree
        min_samples_split = 5,      # min samples to split a node
        min_samples_leaf  = 2,      # min samples at a leaf
        class_weight  = "balanced", # handles imbalance at tree level
        random_state  = 42,
        n_jobs        = -1,         # use all CPU cores
        verbose       = 1
    )

    model.fit(
        X_train_bal,
        y_train_bal,
        sample_weight=sample_weights
    )

    # ── Predictions & Evaluation
    y_pred = model.predict(X_test)

    print("\n── Model Evaluation ──")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}\n")
    print("Classification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    return model


# ── 3. COMPARE MODELS ─────────────────────────────────────────────────────────
def compare_with_xgboost(rf_model, X_test, y_test):
    xgb_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', '..', 'models', 'xgboost_model.pkl'  # ← up 2 levels then into models/
    )

    if not os.path.exists(xgb_path):
        print("\nXGBoost model not found — skipping comparison")
        return

    xgb_model = joblib.load(xgb_path)

    rf_pred   = rf_model.predict(X_test)
    xgb_pred  = xgb_model.predict(X_test)

    rf_acc    = accuracy_score(y_test, rf_pred)
    xgb_acc   = accuracy_score(y_test, xgb_pred)

    print("\n── Model Comparison ──")
    print(f"{'Model':<20} {'Accuracy':<12}")
    print("-" * 32)
    print(f"{'Random Forest':<20} {rf_acc:.4f}")
    print(f"{'XGBoost':<20} {xgb_acc:.4f}")
    print("-" * 32)

    winner = "Random Forest" if rf_acc >= xgb_acc else "XGBoost"
    print(f"Best model: {winner}")

    # ── Bar chart comparison
    fig, ax = plt.subplots(figsize=(8, 5))
    models  = ["Random Forest", "XGBoost"]
    scores  = [rf_acc, xgb_acc]
    colors  = ["#3b82f6", "#f59e0b"]

    bars = ax.bar(models, scores, color=colors, width=0.4)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Accuracy")
    ax.set_title("Model Comparison — Random Forest vs XGBoost")

    for bar, score in zip(bars, scores):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.01,
            f"{score:.4f}",
            ha="center", va="bottom", fontweight="bold"
        )

    plt.tight_layout()
    plt.savefig("model_comparison.png")
    plt.show()
    print("Comparison chart saved to model_comparison.png")


# ── 4. FEATURE IMPORTANCE ─────────────────────────────────────────────────────
def plot_feature_importance(model, X_train):
    importance = pd.Series(
        model.feature_importances_,
        index=X_train.columns
    ).sort_values(ascending=False)

    print("\n── Feature Importances ──")
    print(importance)

    importance.plot(
        kind="bar", figsize=(10, 5),
        title="Random Forest Feature Importances",
        color="#3b82f6"
    )
    plt.tight_layout()
    plt.savefig("rf_feature_importance.png")
    plt.show()
    print("Feature importance plot saved to rf_feature_importance.png")


# ── 5. ML PRIORITIZATION ──────────────────────────────────────────────────────
def assign_ml_priority(df, model, X_test):
    """
    Isolation Forest on behavioral features — same approach as XGBoost pipeline.
    """
    behavioral_features = [
        "hour", "day_of_week", "is_weekend",
        "computer", "user", "level", "keyword"
    ]
    available    = [f for f in behavioral_features if f in X_test.columns]
    X_behavioral = X_test[available]

    iso        = IsolationForest(contamination=0.1, random_state=42)
    iso.fit(X_behavioral)
    raw_scores = iso.decision_function(X_behavioral)
    min_s      = raw_scores.min()
    max_s      = raw_scores.max()
    risk_score = 1 - (raw_scores - min_s) / (max_s - min_s)

    df = df.copy()
    df["risk_score"] = risk_score
    df["priority"]   = pd.cut(
        risk_score,
        bins           = [0, 0.33, 0.66, 1.0],
        labels         = ["Low", "Medium", "High"],
        include_lowest = True
    )

    print("\n── ML Priority Distribution (Random Forest) ──")
    print(df["priority"].value_counts())
    print(f"\nAverage risk score : {risk_score.mean():.4f}")

    return df


# ── 6. SAVE MODEL ─────────────────────────────────────────────────────────────
def save_model(model, path="random_forest_model.pkl"):
    """Save trained model to disk using joblib."""
    joblib.dump(model, path)
    print(f"\nModel saved to: {path}")


# ── 7. LOAD MODEL ─────────────────────────────────────────────────────────────
def load_model(path="random_forest_model.pkl"):
    """Load a saved Random Forest model."""
    model = joblib.load(path)
    print(f"\nModel loaded from: {path}")
    return model


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":

    if conn is None:
        print("No database connection — exiting")
        sys.exit(1)

    # Load data
    df = get_events(conn)
    X_train, X_test, y_train, y_test = process_data(df)

    # Train
    model = train_random_forest(X_train, X_test, y_train, y_test)

   
    # ── Save to models/ folder explicitly
    models_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', '..', 'models', 'random_forest_model.pkl'
    )
    save_model(model, path=models_path)

    # Feature importance
    plot_feature_importance(model, X_train)

    # Prioritization
    df_test        = X_test.copy()
    df_prioritized = assign_ml_priority(df_test, model, X_test)
    df_prioritized.to_csv("rf_prioritized_events.csv", index=False)
    print("\nPrioritized events saved to rf_prioritized_events.csv ✓")

    # Compare with XGBoost
    compare_with_xgboost(model, X_test, y_test)

    conn.close()
    print("\nDone ✓")