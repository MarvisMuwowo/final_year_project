# backend/app/ML/retrain.py
import pandas as pd
import numpy as np
import joblib
import os
import sys
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from imblearn.combine import SMOTETomek
from imblearn.over_sampling import SMOTE
from collections import Counter
from pandas.api.types import is_numeric_dtype

# Add paths to import preprocess
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'service')))
from preprocess import FEATURE_COLS

def prepare_training_data(events_df, feedback_df=None):
    """
    Prepare training data: merge feedback corrections.
    Returns X (features), y (target labels), encoders, scaler, target_encoder.
    """
    data = events_df.copy()
    target_col = "task_category"
    
    # Ensure logged is datetime for time features
    if "logged" in data.columns:
        data["logged"] = pd.to_datetime(data["logged"], errors="coerce")
        data["hour"] = data["logged"].dt.hour.fillna(0).astype(int)
        data["day_of_week"] = data["logged"].dt.dayofweek.fillna(0).astype(int)
        data["is_weekend"] = (data["day_of_week"] >= 5).astype(int)
    else:
        data["hour"] = 0
        data["day_of_week"] = 0
        data["is_weekend"] = 0

    # Drop non-feature columns
    drop_cols = ["id", "logged", "status", "assigned_to"]
    data.drop(columns=[c for c in drop_cols if c in data.columns], inplace=True, errors="ignore")
    
    # Merge rare target classes
    if target_col in data.columns:
        counts = data[target_col].value_counts()
        rare = counts[counts < 5].index.tolist()
        if rare:
            data[target_col] = data[target_col].replace(rare, "Other")

    # ── Override target with feedback ──
    if feedback_df is not None and not feedback_df.empty:
        # Only override when is_correctly_classified == False (misclassified)
        # Or we can always override with the latest feedback for each event.
        # We'll use the most recent feedback for each event (if any)
        fb = feedback_df.sort_values("submitted_at").drop_duplicates("event_id", keep="last")
        if not fb.empty:
            correction_map = dict(zip(fb["event_id"], fb["correct_label"]))
            # Apply override
            data[target_col] = data.apply(
                lambda row: correction_map.get(row["event_id"], row[target_col]),
                axis=1
            )
            logger.info(f"Applied feedback corrections for {len(correction_map)} events")
    
    # Feature columns (without event_id)
    feature_cols = FEATURE_COLS
    
    # Encode categorical features
    encoders = {}
    for col in feature_cols:
        if col in data.columns and not is_numeric_dtype(data[col]):
            le = LabelEncoder()
            data[col] = le.fit_transform(data[col].astype(str))
            encoders[col] = le
        elif col not in data.columns:
            # If missing, fill with 0 and warn
            data[col] = 0
            logger.warning(f"Feature column '{col}' missing, filling with 0")
    
    X = data[feature_cols].copy()
    y = data[target_col].copy()
    
    # Encode target labels
    target_encoder = LabelEncoder()
    y_enc = target_encoder.fit_transform(y)
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled_df = pd.DataFrame(X_scaled, columns=feature_cols, index=X.index)
    
    return X_scaled_df, y_enc, encoders, scaler, target_encoder

def apply_resampling(X_train, y_train, random_state=42):
    """SMOTETomek resampling for imbalanced classes."""
    counts = Counter(y_train)
    min_samples = min(counts.values())
    if min_samples < 2:
        return X_train, y_train
    k = min(5, min_samples - 1)
    resampler = SMOTETomek(
        smote=SMOTE(k_neighbors=k, random_state=random_state),
        random_state=random_state
    )
    X_res, y_res = resampler.fit_resample(X_train, y_train)
    return X_res, y_res

def train_xgboost(X_train, X_test, y_train, y_test):
    """Train XGBoost with resampling."""
    X_train_bal, y_train_bal = apply_resampling(X_train, y_train)
    num_classes = len(set(y_train_bal))
    model = XGBClassifier(
        objective="multi:softprob",
        num_class=num_classes,
        eval_metric="mlogloss",
        use_label_encoder=False,
        n_estimators=500,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=1,
        gamma=0,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        tree_method="hist",
        early_stopping_rounds=30
    )
    model.fit(
        X_train_bal, y_train_bal,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    return model

def train_random_forest(X_train, X_test, y_train, y_test):
    """Train Random Forest with resampling."""
    X_train_bal, y_train_bal = apply_resampling(X_train, y_train)
    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=8,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
        verbose=0
    )
    model.fit(X_train_bal, y_train_bal)
    return model

def train_catboost(X_train, X_test, y_train, y_test):
    """Train CatBoost with resampling."""
    X_train_bal, y_train_bal = apply_resampling(X_train, y_train)
    model = CatBoostClassifier(
        iterations=500,
        depth=8,
        learning_rate=0.05,
        loss_function='MultiClass',
        eval_metric='Accuracy',
        random_seed=42,
        verbose=False,
        use_best_model=True,
        early_stopping_rounds=30
    )
    model.fit(X_train_bal, y_train_bal, eval_set=(X_test, y_test), verbose=False)
    return model

def retrain_all_models(events_df, feedback_df=None):
    """
    Retrain all models using corrected labels from feedback.
    Returns a dict with model artifacts.
    """
    # Prepare training data
    X_full, y_full, encoders, scaler, target_encoder = prepare_training_data(events_df, feedback_df)
    
    # Split into train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X_full, y_full, test_size=0.20, random_state=42, stratify=y_full
    )
    
    # Train models
    models = {}
    print("Training XGBoost...")
    models["xgboost"] = train_xgboost(X_train, X_test, y_train, y_test)
    print("Training Random Forest...")
    models["random_forest"] = train_random_forest(X_train, X_test, y_train, y_test)
    print("Training CatBoost...")
    models["catboost"] = train_catboost(X_train, X_test, y_train, y_test)
    
    # Evaluate each
    for name, model in models.items():
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        print(f"{name} accuracy: {acc:.4f}")
    
    # Build artifacts
    artifacts = {}
    for name, model in models.items():
        artifacts[name] = {
            "model": model,
            "target_encoder": target_encoder,
            "encoders": encoders,
            "scaler": scaler,
            "feature_cols": FEATURE_COLS
        }
    return artifacts