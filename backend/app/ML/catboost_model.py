# backend/app/ML/catboost_model.py
import pandas as pd
import psycopg2
from catboost import CatBoostClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
from imblearn.combine import SMOTETomek
from imblearn.over_sampling import SMOTE
from collections import Counter
import joblib
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'service')))
from preprocess import process_data, FEATURE_COLS

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

if conn is None:
    sys.exit(1)

df = get_events(conn)
X_train, X_test, y_train, y_test, encoders, scaler = process_data(df)

# ── ENCODE TARGET LABELS ──────────────────────────────────────────────────────
target_encoder = LabelEncoder()
y_train_enc = target_encoder.fit_transform(y_train)
y_test_enc = target_encoder.transform(y_test)

print("\n── Target Classes ──")
for idx, label in enumerate(target_encoder.classes_):
    print(f"{idx}: {label}")

# ── RESAMPLING ────────────────────────────────────────────────────────────────
def apply_resampling(X_train, y_train, random_state=42):
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

# ── TRAIN ─────────────────────────────────────────────────────────────────────
def train_catboost(X_train, X_test, y_train, y_test):
    print("\n── Training CatBoost Model ──")

    X_train_bal, y_train_bal = apply_resampling(X_train, y_train)

    model = CatBoostClassifier(
        iterations=500,
        depth=8,
        learning_rate=0.05,
        loss_function='MultiClass',
        eval_metric='Accuracy',
        random_seed=42,
        verbose=50,
        use_best_model=True,
        early_stopping_rounds=30,
    )

    model.fit(
        X_train_bal,
        y_train_bal,
        eval_set=(X_test, y_test),
        verbose=50,
        plot=False,
    )

    y_pred = model.predict(X_test)
    y_pred = y_pred.flatten()

    # Decode for readable evaluation
    y_pred_labels = target_encoder.inverse_transform(y_pred)
    y_test_labels = target_encoder.inverse_transform(y_test)

    print("\n── Model Evaluation ──")
    print(f"Accuracy: {accuracy_score(y_test_labels, y_pred_labels):.4f}\n")
    print("Classification Report:")
    print(classification_report(y_test_labels, y_pred_labels, zero_division=0))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test_labels, y_pred_labels))

    return model

# ── SAVE MODEL ────────────────────────────────────────────────────────────────
def save_model(model, target_encoder, encoders, scaler, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump({
        "model": model,
        "target_encoder": target_encoder,
        "encoders": encoders,
        "scaler": scaler,
        "feature_cols": FEATURE_COLS
    }, path)
    print(f"\n✅ Model and preprocessing objects saved to: {path}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    model = train_catboost(X_train, X_test, y_train_enc, y_test_enc)

    # ─── SAVE TO backend/app/ML/models/ ──────────────────────────────────
    script_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(script_dir, 'models')
    models_path = os.path.join(models_dir, 'catboost_model.pkl')
    print(f"\nSaving to: {models_path}")
    save_model(model, target_encoder, encoders, scaler, path=models_path)

    # Feature importances
    importance = pd.Series(
        model.feature_importances_,
        index=FEATURE_COLS
    ).sort_values(ascending=False)
    print("\n── Feature Importances ──")
    print(importance)

    conn.close()
    print("\n✅ CatBoost training complete!")