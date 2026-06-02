import pandas as pd
import psycopg2
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.ensemble import IsolationForest
from imblearn.combine import SMOTETomek
from imblearn.over_sampling import SMOTE
from collections import Counter
import numpy as np
import joblib
import matplotlib.pyplot as plt
import sys
import os


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


df = get_events(conn)
X_train, X_test, y_train, y_test = process_data(df)


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


# ── 2. TRAIN ──────────────────────────────────────────────────────────────────
def train_xgboost(X_train, X_test, y_train, y_test):
    """
    Train a multi-class XGBoost classifier with imbalance-aware techniques.
    """
    print("\n── Training XGBoost Model ──")

    X_train_bal, y_train_bal = apply_resampling(X_train, y_train)
    sample_weights = compute_sample_weight(class_weight="balanced", y=y_train_bal)
    num_classes    = len(set(y_train_bal))

    model = XGBClassifier(
        objective         = "multi:softprob",
        num_class         = num_classes,
        eval_metric       = "mlogloss",
        use_label_encoder = False,
        n_estimators      = 500,
        max_depth         = 8,
        learning_rate     = 0.05,
        subsample         = 0.8,
        colsample_bytree  = 0.8,
        min_child_weight  = 1,
        gamma             = 0,
        reg_alpha         = 0.1,
        reg_lambda        = 1.0,
        random_state      = 42,
        tree_method       = "hist",
        early_stopping_rounds = 30,
    )

    model.fit(
        X_train_bal,
        y_train_bal,
        sample_weight = sample_weights,
        eval_set      = [(X_test, y_test)],
        verbose       = 50,
    )

    y_pred = model.predict(X_test)

    print("\n── Model Evaluation ──")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}\n")
    print("Classification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    return model


# ── 3. SAVE MODEL ─────────────────────────────────────────────────────────────
def save_model(model, path="xgboost_model.pkl"):
    """Save trained model to disk using joblib."""
    joblib.dump(model, path)
    print(f"\nModel saved to: {path}")


# ── 4. LOAD MODEL ─────────────────────────────────────────────────────────────
def load_model(path="xgboost_model.pkl"):
    """Load a saved XGBoost model."""
    model = joblib.load(path)
    print(f"\nModel loaded from: {path}")
    return model


# ── 5. ML PRIORITIZATION ──────────────────────────────────────────────────────
def assign_ml_priority(df, model, X_test):
    """
    Isolation Forest on behavioral features only.
    Flags events that don't fit normal patterns as high priority.
    No manual rules — purely data driven.
    """
    print("\n── Running Isolation Forest Prioritization ──")

    # Behavioral features only — deliberately excludes event_id
    # so priority is based on WHEN/WHERE events happen, not just what they are
    behavioral_features = [
        "hour", "day_of_week", "is_weekend",
        "computer", "user", "level", "keyword"
    ]

    available    = [f for f in behavioral_features if f in X_test.columns]
    X_behavioral = X_test[available]

    print(f"  Behavioral features used: {available}")

    # Train Isolation Forest — learns what normal looks like
    # contamination=0.1 means assume 10% of events are anomalous
    iso = IsolationForest(contamination=0.1, random_state=42)
    iso.fit(X_behavioral)

    # decision_function: more negative = more anomalous
    raw_scores = iso.decision_function(X_behavioral)

    # Normalize to 0-1 range (1 = most anomalous = highest priority)
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

    print("\n── ML Priority Distribution ──")
    print(df["priority"].value_counts())
    print(f"\nAverage risk score : {risk_score.mean():.4f}")
    print(f"\nTop 10 highest risk events:")
    print(df.nlargest(10, "risk_score")[["risk_score", "priority"]])

    return df


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # ── Train
    model = train_xgboost(X_train, X_test, y_train, y_test)

    # ── Save to models/ folder explicitly
    models_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', '..', 'models', 'xgboost_model.pkl'
    )
    save_model(model, path=models_path)

    # ── Feature Importances
    importance = pd.Series(
        model.feature_importances_,
        index=X_train.columns
    ).sort_values(ascending=False)

    print("\n── Feature Importances ──")
    print(importance)

    importance.plot(kind="bar", figsize=(10, 5), title="Feature Importances")
    plt.tight_layout()
    plt.savefig("feature_importance.png")
    print("Feature importance plot saved")

    # ── ML Prioritization
    df_test        = X_test.copy()
    df_prioritized = assign_ml_priority(df_test, model, X_test)

    # Save prioritized results
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "data", "prioritized_events.csv"
    )
    df_prioritized.to_csv(output_path, index=False)
    print(f"\nPrioritized events saved to: {output_path} ✓")


    import shap



print("\n── SHAP Explanation ──")
explainer   = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# Global summary — which features matter most
shap.summary_plot(shap_values, X_test, show=False)
plt.savefig("shap_summary.png", bbox_inches="tight")
plt.show()                          # ← displays on screen
plt.clf()
print("SHAP summary plot saved to shap_summary.png")

# Bar plot — mean absolute SHAP values
shap.summary_plot(shap_values, X_test, plot_type="bar", show=False)
plt.savefig("shap_bar.png", bbox_inches="tight")
plt.show()                          # ← displays on screen
plt.clf()
print("SHAP bar plot saved to shap_bar.png")

# Single event explanation — shows why ONE specific event was classified
print("\n── Single Event SHAP Explanation ──")
shap.waterfall_plot(
    shap.Explanation(
        values        = shap_values[0][0],
        base_values   = explainer.expected_value[0],
        data          = X_test.iloc[0],
        feature_names = X_test.columns.tolist()
    )
)
plt.savefig("shap_single.png", bbox_inches="tight")
plt.show()                          # ← displays on screen
print("Single event SHAP plot saved to shap_single.png")