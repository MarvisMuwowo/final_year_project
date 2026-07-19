# backend/app/API/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import joblib
import shap
import numpy as np
import sys
import os
import bcrypt as bcrypt_lib
from sklearn.ensemble import IsolationForest
from typing import List
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# ── Scheduler imports ──
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import threading

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'database'))
from config import DB_CONFIG

from app.API.dependencies import (
    get_current_user, get_db_connection, get_user_from_db,
    _cache, set_model, SECRET_KEY, ALGORITHM
)

from app.API.classification import router as classification_router, init_feedback_table
from app.API.shap_explainer import router as shap_router

# ── Import retrain module ──
from app.ML.retrain import retrain_all_models

load_dotenv()

# ── SMTP ──────────────────────────────────────────────────────────────────────
SMTP_HOST         = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT         = int(os.getenv("SMTP_PORT", 587))
SMTP_USER         = os.getenv("SMTP_USER", "")
SMTP_PASSWORD     = os.getenv("SMTP_PASSWORD", "")
FALLBACK_RECIPIENTS = [
    e.strip() for e in os.getenv("SMTP_RECIPIENTS", "").split(",")
    if e.strip()
]

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("high_priority_alerts.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ACCESS_TOKEN_EXPIRE_MINUTES = 60

app = FastAPI(title="Windows Security Log Prioritization API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(classification_router)
app.include_router(shap_router)

# ── Load model artifact ───────────────────────────────────────────────────────
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'ML', 'models', 'xgboost_model.pkl'
)

if not os.path.exists(MODEL_PATH):
    logger.error(f"Model file not found at {MODEL_PATH}")
    raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")

artifact      = joblib.load(MODEL_PATH)
model         = artifact["model"]
target_encoder = artifact["target_encoder"]
encoders      = artifact["encoders"]
scaler        = artifact["scaler"]
feature_cols  = artifact["feature_cols"]

set_model(model)
logger.info(f"Model loaded. Feature cols: {feature_cols}")

# ── Thread lock and polling flag ──────────────────────────────────────────────
_process_lock    = threading.Lock()
_polling_enabled = True

# ── JSON serialization helper ──────────────────────────────────────────────
def convert_to_serializable(obj):
    if isinstance(obj, (np.integer, np.floating)):
        if pd.isna(obj):
            return None
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(v) for v in obj]
    elif isinstance(obj, pd.Series):
        return convert_to_serializable(obj.tolist())
    elif isinstance(obj, pd.DataFrame):
        # Replace NaN with None
        obj = obj.where(pd.notnull(obj), None)
        return convert_to_serializable(obj.to_dict(orient="records"))
    else:
        return obj

# ── Pydantic models ───────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token : str
    token_type   : str
    role         : str
    username     : str

class UserCreate(BaseModel):
    username : str
    email    : EmailStr
    password : str
    role     : str = "security_analyst"

class UserResponse(BaseModel):
    id        : int
    username  : str
    email     : str
    role      : str
    is_active : bool

class StatusUpdate(BaseModel):
    status      : str
    assigned_to : str = ""

class AddEventsRequest(BaseModel):
    event_ids: List[int]

# ── Auth helpers ──────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt_lib.hashpw(
        password.encode("utf-8"), bcrypt_lib.gensalt()
    ).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt_lib.checkpw(
            plain.encode("utf-8"), hashed.encode("utf-8")
        )
    except Exception:
        return False

def create_access_token(data: dict):
    to_encode = data.copy()
    expire    = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ── Email helpers ─────────────────────────────────────────────────────────────
def get_recipients():
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT email FROM users
            WHERE is_active = TRUE
              AND role IN ('security_analyst', 'admin', 'system_admin')
              AND email IS NOT NULL AND email != ''
        """)
        emails = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return emails if emails else FALLBACK_RECIPIENTS
    except Exception as e:
        logger.error(f"Error fetching recipients: {e}")
        return FALLBACK_RECIPIENTS

def send_email_alert(row):
    recipients = get_recipients()
    if not recipients or not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("Email alert skipped — no recipients or SMTP not configured")
        return False

    subject = f"🚨 HIGH PRIORITY EVENT — Event #{row.get('id', 'N/A')}"
    body    = (
        f"🚨 HIGH PRIORITY EVENT ALERT 🚨\n\n"
        f"  ID            : {row.get('id', 'N/A')}\n"
        f"  Event ID      : {row.get('event_id', 'N/A')}\n"
        f"  Priority      : {row.get('priority', 'High')}\n"
        f"  Risk Score    : {row.get('risk_score', 0.0):.4f}\n"
        f"  Logged at     : {row.get('logged',    'N/A')}\n"
        f"  Computer      : {row.get('computer',  'N/A')}\n"
        f"  User          : {row.get('user',      'N/A')}\n"
        f"  Level         : {row.get('level',     'N/A')}\n\n"
        f"Please investigate immediately."
    )
    msg           = MIMEMultipart()
    msg["From"]   = SMTP_USER
    msg["To"]     = ", ".join(recipients)
    msg["Subject"]= subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, recipients, msg.as_string())
        server.quit()
        logger.info(f"Email alert sent for Event {row.get('id', 'N/A')}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def alert_high_priority_events(events_df, new_only=True):
    if events_df is None or events_df.empty:
        return 0
    last_time = _cache.get(
        "last_alert_time",
        datetime.min.replace(tzinfo=timezone.utc)
    )
    high_df = events_df[events_df["priority"] == "High"]
    if new_only and "logged" in high_df.columns:
        high_df = high_df[
            pd.to_datetime(high_df["logged"], utc=True) > last_time
        ]
    if high_df.empty:
        return 0
    for _, row in high_df.iterrows():
        logger.warning(
            f"🚨 HIGH PRIORITY: ID {row.get('id','N/A')} "
            f"risk={row.get('risk_score',0):.4f}"
        )
        send_email_alert(row)
    _cache["last_alert_time"] = datetime.now(timezone.utc)
    return len(high_df)

# ── Database init ─────────────────────────────────────────────────────────────
def init_database():
    conn   = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DO $$ BEGIN
                CREATE TYPE user_role AS ENUM
                    ('security_analyst', 'system_admin', 'admin', 'viewer');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            SERIAL PRIMARY KEY,
                username      VARCHAR(50)  UNIQUE NOT NULL,
                email         VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role          user_role DEFAULT 'security_analyst',
                is_active     BOOLEAN   DEFAULT TRUE,
                last_login    TIMESTAMP,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='events' AND column_name='status'
                ) THEN
                    ALTER TABLE events ADD COLUMN status VARCHAR(20) DEFAULT 'unassigned';
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='events' AND column_name='assigned_to'
                ) THEN
                    ALTER TABLE events ADD COLUMN assigned_to VARCHAR(50) DEFAULT NULL;
                END IF;
            END $$;
        """)
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

# ── Transform helper ──────────────────────────────────────────────────────────
def transform_df(df):
    data = df.copy()

    if "logged" in data.columns:
        data["logged"] = pd.to_datetime(data["logged"], errors="coerce", utc=True)
        data["hour"]        = data["logged"].dt.hour.fillna(0).astype(int)
        data["day_of_week"] = data["logged"].dt.dayofweek.fillna(0).astype(int)
        data["is_weekend"]  = (data["day_of_week"] >= 5).astype(int)
    else:
        data["hour"]        = 0
        data["day_of_week"] = 0
        data["is_weekend"]  = 0

    for col in feature_cols:
        if col in encoders:
            le = encoders[col]
            if col not in data.columns:
                data[col] = le.classes_[0]
            known = set(le.classes_)
            data[col] = data[col].astype(str).apply(
                lambda x: x if x in known else le.classes_[0]
            )
            data[col] = le.transform(data[col])

    missing_cols = [c for c in feature_cols if c not in data.columns]
    for c in missing_cols:
        logger.warning(f"Feature column '{c}' missing, filling with 0")
        data[c] = 0

    X = data[feature_cols].copy()
    X_scaled    = scaler.transform(X)
    X_scaled_df = pd.DataFrame(X_scaled, columns=feature_cols, index=data.index)
    return X_scaled_df

# ── Cache builder ─────────────────────────────────────────────────────────────
def get_events_df():
    conn = get_db_connection()
    df   = pd.read_sql("SELECT * FROM events", conn)
    conn.close()
    if "logged" in df.columns:
        df["logged"] = pd.to_datetime(df["logged"], errors="coerce", utc=True)
    return df

def _score_and_build_result(X_features, df_original):
    y_pred = model.predict(X_features)
    y_pred = np.array([int(round(float(p))) for p in y_pred])
    n_classes = len(target_encoder.classes_) if hasattr(target_encoder, "classes_") else 5
    y_pred = np.clip(y_pred, 0, n_classes - 1)

    behavioral = ["hour", "day_of_week", "is_weekend",
                  "computer", "user", "level", "keyword"]
    avail        = [c for c in behavioral if c in X_features.columns]
    X_behavioral = X_features[avail]

    iso        = IsolationForest(contamination=0.1, random_state=42)
    iso.fit(X_behavioral)
    raw_scores = iso.decision_function(X_behavioral)
    min_s, max_s = raw_scores.min(), raw_scores.max()
    risk_score   = 1 - (raw_scores - min_s) / (max_s - min_s + 1e-9)

    result              = X_features.copy()
    result["predicted"] = y_pred
    result["risk_score"]= risk_score
    result["priority"]  = pd.cut(
        risk_score,
        bins=[0, 0.33, 0.66, 1.0],
        labels=["Low", "Medium", "High"],
        include_lowest=True
    ).astype(str)

    display_cols = ["id", "event_id", "logged", "status", "assigned_to",
                    "computer", "user", "level", "keyword", "task_category"]
    merge_cols   = [c for c in display_cols if c in df_original.columns]

    if "id" in df_original.columns:
        result["id"] = df_original["id"].values
        result = result.merge(
            df_original[merge_cols].drop_duplicates("id"),
            on="id", how="left"
        )
    elif "event_id" in df_original.columns:
        result["event_id"] = df_original["event_id"].values
        result = result.merge(
            df_original[merge_cols].drop_duplicates("event_id"),
            on="event_id", how="left"
        )
    else:
        for c in merge_cols:
            if c != "event_id" and c != "id":
                result[c] = df_original[c].values if c in df_original.columns else None

    result["status"]      = result["status"].fillna("unassigned")
    result["assigned_to"] = result["assigned_to"].fillna("")
    result["worked_on"]   = False

    # ── Clean NaN in id and event_id ──
    if "id" in result.columns:
        result["id"] = result["id"].fillna(0).astype(int)
    if "event_id" in result.columns:
        result["event_id"] = result["event_id"].fillna(0).astype(int)

    return result, iso, min_s, max_s

def build_cache():
    logger.info("\n── Building data cache (in-memory) ──")
    _cache.clear()
    df = get_events_df()

    if df.empty:
        logger.warning("No events in database — cache will be empty")
        _cache.update({
            "df_raw"          : df,
            "X_test"          : pd.DataFrame(columns=feature_cols),
            "result"          : pd.DataFrame(),
            "priority_counts" : {},
            "shap_values"     : None,
            "explainer"       : None,
            "feature_importance": {},
            "iso"             : None,
            "iso_min"         : 0,
            "iso_max"         : 1,
            "feature_cols"    : feature_cols,
            "encoders"        : encoders,
            "scaler"          : scaler,
            "target_encoder"  : target_encoder,
            "active_model"    : _cache.get("active_model", "xgboost"),
            "last_alert_time" : datetime.min.replace(tzinfo=timezone.utc),
            "built_at"        : datetime.now(timezone.utc).isoformat(),
        })
        return

    X_features = transform_df(df)
    logger.info(f"Transformed full dataset: {X_features.shape} rows")

    result, iso, iso_min, iso_max = _score_and_build_result(X_features, df)

    result = result.reset_index(drop=True)
    priority_counts = result["priority"].value_counts().to_dict()

    logger.info("  Computing SHAP values on full dataset...")
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_features)
    logger.info(f"SHAP values computed: {shap_values[0].shape[0] if isinstance(shap_values, list) else shap_values.shape[0]} rows")

    try:
        feature_importance = dict(zip(feature_cols, model.feature_importances_))
        logger.info("Feature importance from model")
    except (AttributeError, TypeError):
        if shap_values is not None:
            if isinstance(shap_values, list):
                all_shap = np.abs(np.array(shap_values))
            else:
                all_shap = np.abs(np.array(shap_values))[np.newaxis, ...]
            mean_abs = all_shap.mean(axis=(0, 1)).tolist()
            feature_importance = dict(zip(feature_cols, mean_abs))
            logger.info("Feature importance computed from SHAP (fallback)")
        else:
            feature_importance = {col: 0.0 for col in feature_cols}
            logger.warning("Feature importance set to zeros (no data)")

    feature_importance = {k: (0.0 if pd.isna(v) else v) for k, v in feature_importance.items()}

    # ── Set last_processed_time ──
    if "logged" in df.columns and not df["logged"].isna().all():
        last_time = df["logged"].max()
        if last_time.tzinfo is None:
            last_time = last_time.tz_localize("UTC")
    else:
        last_time = datetime.min.replace(tzinfo=timezone.utc)

    _cache.update({
        "df_raw"             : df,
        "X_test"             : X_features,
        "result"             : result,
        "priority_counts"    : priority_counts,
        "shap_values"        : shap_values,
        "explainer"          : explainer,
        "feature_importance" : feature_importance,
        "iso"                : iso,
        "iso_min"            : iso_min,
        "iso_max"            : iso_max,
        "feature_cols"       : feature_cols,
        "encoders"           : encoders,
        "scaler"             : scaler,
        "target_encoder"     : target_encoder,
        "active_model"       : _cache.get("active_model", "xgboost"),
        "last_alert_time"    : datetime.min.replace(tzinfo=timezone.utc),
        "last_processed_time": last_time,
        "built_at"           : datetime.now(timezone.utc).isoformat(),
    })

    alert_high_priority_events(result, new_only=True)

    logger.info(f"  High   : {priority_counts.get('High',   0)}")
    logger.info(f"  Medium : {priority_counts.get('Medium', 0)}")
    logger.info(f"  Low    : {priority_counts.get('Low',    0)}")
    logger.info(f"  Total  : {len(result)}")
    logger.info("── Cache ready ✓ ──\n")

    joblib.dump(_cache, "cache_full.pkl")
    logger.info("Cache saved to cache_full.pkl")

# ── Incremental update function ──
def process_new_events():
    global _polling_enabled
    if not _polling_enabled:
        return

    if not _process_lock.acquire(blocking=False):
        logger.info("Previous process_new_events still running, skipping")
        return

    try:
        last_time = _cache.get("last_processed_time", datetime.min.replace(tzinfo=timezone.utc))
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)

        conn = get_db_connection()
        query = "SELECT * FROM events WHERE logged > %s ORDER BY logged ASC"
        # Convert last_time to a Python datetime (psycopg2 handles it)
        new_df = pd.read_sql(query, conn, params=(last_time,))
        conn.close()

        if new_df.empty:
            return

        if "logged" in new_df.columns:
            new_df["logged"] = pd.to_datetime(new_df["logged"], errors="coerce", utc=True)

        logger.info(f"Found {len(new_df)} new events since {last_time}")

        X_new = transform_df(new_df)
        X_new_features = X_new[feature_cols]

        y_pred_new = model.predict(X_new_features)
        y_pred_new = np.array([int(round(float(p))) for p in y_pred_new])
        n_classes = len(target_encoder.classes_) if hasattr(target_encoder, "classes_") else 5
        y_pred_new = np.clip(y_pred_new, 0, n_classes - 1)

        iso = _cache["iso"]
        iso_min = _cache["iso_min"]
        iso_max = _cache["iso_max"]
        behavioral_features = ["hour", "day_of_week", "is_weekend", "computer", "user", "level", "keyword"]
        avail = [c for c in behavioral_features if c in X_new_features.columns]
        X_behavioral_new = X_new_features[avail]
        raw_scores_new = iso.decision_function(X_behavioral_new)
        risk_score_new = 1 - (raw_scores_new - iso_min) / (iso_max - iso_min + 1e-9)

        result_new = X_new_features.copy()
        result_new["predicted"] = y_pred_new
        result_new["risk_score"] = risk_score_new
        result_new["priority"] = pd.cut(
            risk_score_new,
            bins=[0, 0.33, 0.66, 1.0],
            labels=["Low", "Medium", "High"],
            include_lowest=True
        ).astype(str)

        merge_cols = ["event_id", "logged", "status", "assigned_to", "worked_on",
                      "computer", "user", "level", "keyword", "task_category"]
        merge_cols = [c for c in merge_cols if c in new_df.columns]
        if "event_id" in new_df.columns:
            result_new["event_id"] = new_df["event_id"].values
            result_new = result_new.merge(
                new_df[merge_cols].drop_duplicates("event_id"),
                on="event_id", how="left"
            )
        else:
            for c in merge_cols:
                if c in new_df.columns:
                    result_new[c] = new_df[c].values

        result_new["status"] = result_new["status"].fillna("unassigned")
        result_new["assigned_to"] = result_new["assigned_to"].fillna("")
        result_new["worked_on"] = result_new["worked_on"].fillna(False)

        # ── Clean NaN in id and event_id ──
        if "id" in result_new.columns:
            result_new["id"] = result_new["id"].fillna(0).astype(int)
        if "event_id" in result_new.columns:
            result_new["event_id"] = result_new["event_id"].fillna(0).astype(int)

        old_result = _cache["result"]
        old_X_test = _cache["X_test"]
        old_shap = _cache["shap_values"]

        _cache["result"] = pd.concat([old_result, result_new], ignore_index=True)
        _cache["X_test"] = pd.concat([old_X_test, X_new_features], ignore_index=True)

        _cache["result"] = _cache["result"].reset_index(drop=True)
        _cache["result"]["index"] = _cache["result"].index

        _cache["priority_counts"] = _cache["result"]["priority"].value_counts().to_dict()

        explainer = _cache["explainer"]
        shap_new = explainer.shap_values(X_new_features)
        if isinstance(shap_new, list):
            for i in range(len(shap_new)):
                _cache["shap_values"][i] = np.vstack([old_shap[i], shap_new[i]])
        else:
            _cache["shap_values"] = np.vstack([old_shap, shap_new])

        new_last = new_df["logged"].max()
        if new_last.tzinfo is None:
            new_last = new_last.tz_localize("UTC")
        _cache["last_processed_time"] = new_last
        _cache["built_at"] = datetime.now(timezone.utc).isoformat()

        alert_high_priority_events(result_new, new_only=True)

        logger.info(f"Cache updated: +{len(result_new)} events. Total: {len(_cache['result'])}")

    except Exception as e:
        logger.error(f"process_new_events error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        _process_lock.release()

# ── Retrain models using feedback ──
@app.post("/retrain-models")
def retrain_models(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["system_admin", "admin"]:
        raise HTTPException(403, "Only admins can retrain models")

    conn = get_db_connection()
    events_df = pd.read_sql("SELECT * FROM events", conn)
    conn.close()

    feedback_df = None
    try:
        conn = get_db_connection()
        feedback_df = pd.read_sql("SELECT * FROM feedback", conn)
        conn.close()
    except Exception as e:
        logger.warning(f"Feedback table not found or empty: {e}")
        feedback_df = pd.DataFrame()

    try:
        artifacts = retrain_all_models(events_df, feedback_df)
    except Exception as e:
        logger.error(f"Retraining failed: {e}")
        raise HTTPException(500, f"Retraining failed: {e}")

    model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ML', 'models')
    for name, artifact in artifacts.items():
        path = os.path.join(model_dir, f"{name}_model.pkl")
        joblib.dump(artifact, path)
        logger.info(f"Saved {name} model to {path}")

    active_model = _cache.get("active_model", "xgboost")
    artifact_path = os.path.join(model_dir, f"{active_model}_model.pkl")
    new_artifact = joblib.load(artifact_path)
    global model, target_encoder, encoders, scaler, feature_cols
    model = new_artifact["model"]
    target_encoder = new_artifact["target_encoder"]
    encoders = new_artifact["encoders"]
    scaler = new_artifact["scaler"]
    feature_cols = new_artifact["feature_cols"]
    set_model(model)

    build_cache()
    return {"message": "Models retrained and cache rebuilt successfully"}

# ── Model metrics endpoint ──
@app.get("/model-metrics/{model_name}")
def model_metrics(model_name: str, current_user: dict = Depends(get_current_user)):
    # ... (keep as before)
    pass

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    init_database()
    init_feedback_table()

    cache_file = "cache_full.pkl"
    if os.path.exists(cache_file):
        try:
            full_cache = joblib.load(cache_file)
            _cache.clear()
            _cache.update(full_cache)
            logger.info(f"Loaded cache from {cache_file} – {len(_cache['result'])} events")
            # Ensure last_processed_time is set
            if "last_processed_time" not in _cache or _cache["last_processed_time"] == datetime.min.replace(tzinfo=timezone.utc):
                if "result" in _cache and not _cache["result"].empty and "logged" in _cache["result"].columns:
                    last_time = _cache["result"]["logged"].max()
                    if pd.isna(last_time):
                        last_time = datetime.min.replace(tzinfo=timezone.utc)
                    else:
                        if last_time.tzinfo is None:
                            last_time = last_time.tz_localize("UTC")
                    _cache["last_processed_time"] = last_time
                    logger.info(f"Set last_processed_time from loaded cache: {last_time}")
                else:
                    _cache["last_processed_time"] = datetime.min.replace(tzinfo=timezone.utc)
            if "feature_importance" not in _cache or not _cache["feature_importance"]:
                logger.warning("Loaded cache has empty feature_importance – rebuilding...")
                build_cache()
        except Exception as e:
            logger.error(f"Failed to load cache from {cache_file}: {e}. Rebuilding...")
            build_cache()
    else:
        logger.info("No cache file found. Building from scratch...")
        build_cache()

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=process_new_events,
        trigger=IntervalTrigger(seconds=30),
        id='new_events_job',
        replace_existing=True
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    logger.info("Background scheduler started – checking every 30 seconds")

    logger.info("API started.")

# ── ROOT ──────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Windows Security Log Prioritization API is running"}

# ── LOGIN ─────────────────────────────────────────────────────────────────────
@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_from_db(form_data.username)
    if not user:
        raise HTTPException(401, "Incorrect username or password")
    if not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect username or password")
    if not user.get("is_active", False):
        raise HTTPException(403, "Account is disabled")

    conn = cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login = %s WHERE username = %s",
            (datetime.now(timezone.utc), form_data.username)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating last_login: {e}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return {
        "access_token": token,
        "token_type"  : "bearer",
        "role"        : user["role"],
        "username"    : user["username"]
    }

# ── REGISTER ──────────────────────────────────────────────────────────────────
@app.post("/register")
def register(user: UserCreate):
    if len(user.password.encode("utf-8")) > 72:
        raise HTTPException(400, "Password too long — maximum 72 characters")
    valid_roles = ["security_analyst", "system_admin", "admin", "viewer"]
    if user.role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {', '.join(valid_roles)}")

    conn = cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE username = %s", (user.username,))
        if cursor.fetchone():
            raise HTTPException(400, f"Username '{user.username}' already exists")

        cursor.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cursor.fetchone():
            raise HTTPException(400, f"Email '{user.email}' already registered")

        hashed_pw = hash_password(user.password)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, %s::user_role)
            RETURNING id, username, email, role
        """, (user.username, user.email, hashed_pw, user.role))

        conn.commit()
        new_user = cursor.fetchone()

        return {
            "message": f"User {user.username} created successfully",
            "user"   : {
                "id"      : new_user[0],
                "username": new_user[1],
                "email"   : new_user[2],
                "role"    : new_user[3]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(400, f"Registration failed: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

# ── ME ────────────────────────────────────────────────────────────────────────
@app.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    user = get_user_from_db(current_user["username"])
    if not user:
        raise HTTPException(404, "User not found")
    return UserResponse(
        id       =user["id"],
        username =user["username"],
        email    =user["email"],
        role     =user["role"],
        is_active=user["is_active"]
    )

# ── PROTECTED ENDPOINTS ───────────────────────────────────────────────────────
@app.get("/events")
def get_events(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM events", conn)
    conn.close()
    df = df.where(pd.notnull(df), None)
    return convert_to_serializable(df.to_dict(orient="records"))

@app.get("/priority-summary")
def priority_summary(current_user: dict = Depends(get_current_user)):
    counts = _cache["priority_counts"]
    return {
        "High"    : int(counts.get("High",   0)),
        "Medium"  : int(counts.get("Medium", 0)),
        "Low"     : int(counts.get("Low",    0)),
        "Total"   : len(_cache["result"]),
        "username": current_user["username"],
        "role"    : current_user["role"]
    }

@app.get("/prioritized")
def get_prioritized_events(current_user: dict = Depends(get_current_user)):
    result = _cache["result"]
    cols = ["id", "event_id", "risk_score", "priority", "logged", "status", "assigned_to", "worked_on"]
    cols = [c for c in cols if c in result.columns]
    df = result[cols].copy()
    # Ensure event_id is not NaN
    if "event_id" in df.columns:
        df["event_id"] = df["event_id"].fillna(0).astype(int)
    if "id" in df.columns:
        df["id"] = df["id"].fillna(0).astype(int)
    df = df.where(pd.notnull(df), None)
    return convert_to_serializable(df.to_dict(orient="records"))

@app.get("/feature-importance")
def feature_importance(current_user: dict = Depends(get_current_user)):
    fi = _cache.get("feature_importance", {})
    fi = {k: (0.0 if pd.isna(v) else v) for k, v in fi.items()}
    return convert_to_serializable(fi)

@app.get("/active-model")
def get_active_model(current_user: dict = Depends(get_current_user)):
    return {"active_model": _cache.get("active_model", "xgboost")}

@app.get("/cache-timestamp")
def get_cache_timestamp(current_user: dict = Depends(get_current_user)):
    return {"timestamp": _cache.get("built_at", "Not built")}

# ── ADMIN ONLY ────────────────────────────────────────────────────────────────
@app.post("/switch-model/{model_name}")
def switch_model(model_name: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["system_admin", "admin"]:
        raise HTTPException(403, "Only admins can switch models")
    valid_models = ["xgboost", "random_forest", "catboost"]
    if model_name not in valid_models:
        raise HTTPException(400, f"Invalid model. Choose from: {valid_models}")
    model_files = {
        "xgboost"      : "xgboost_model.pkl",
        "random_forest": "random_forest_model.pkl",
        "catboost"     : "catboost_model.pkl"
    }
    model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'ML', 'models', model_files[model_name]
    )
    if not os.path.exists(model_path):
        raise HTTPException(404, f"{model_name} model not found — train it first")
    new_artifact = joblib.load(model_path)
    global model, target_encoder, encoders, scaler, feature_cols
    model          = new_artifact["model"]
    target_encoder = new_artifact["target_encoder"]
    encoders       = new_artifact["encoders"]
    scaler         = new_artifact["scaler"]
    feature_cols   = new_artifact["feature_cols"]
    set_model(model)
    _cache["active_model"] = model_name
    build_cache()
    return {
        "message"     : f"Switched to {model_name} successfully",
        "active_model": model_name,
        "switched_by" : current_user["username"]
    }

@app.post("/refresh-cache")
def refresh_cache(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["system_admin", "admin"]:
        raise HTTPException(403, "Only admins can refresh the cache")
    build_cache()
    return {
        "message": "Cache refreshed successfully",
        "total"  : len(_cache["result"])
    }

@app.post("/events/{event_id}/status")
def update_event_status(event_id: int, update: StatusUpdate, current_user: dict = Depends(get_current_user)):
    valid_statuses = ["unassigned", "in_progress", "resolved"]
    if update.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Choose from {valid_statuses}")
    conn   = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE events
            SET status = %s, assigned_to = %s
            WHERE id = %s
        """, (update.status, update.assigned_to, event_id))
        if cursor.rowcount == 0:
            raise HTTPException(404, "Event not found")
        conn.commit()
        if "result" in _cache:
            _cache["result"].loc[_cache["result"]["id"] == event_id, "status"] = update.status
            _cache["result"].loc[_cache["result"]["id"] == event_id, "assigned_to"] = update.assigned_to
        return {
            "message"    : "Status updated",
            "status"     : update.status,
            "assigned_to": update.assigned_to
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        cursor.close()
        conn.close()

@app.post("/events/{event_id}/worked")
def toggle_worked_on(event_id: int, current_user: dict = Depends(get_current_user)):
    conn   = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT worked_on FROM events WHERE id = %s", (event_id,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(404, "Event not found")
        new_val = not bool(row[0])
        cursor.execute(
            "UPDATE events SET worked_on = %s WHERE id = %s",
            (new_val, event_id)
        )
        conn.commit()
        if "result" in _cache:
            _cache["result"].loc[_cache["result"]["id"] == event_id, "worked_on"] = new_val
        return {"worked_on": new_val}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        cursor.close()
        conn.close()

@app.post("/add-events")
def add_events_to_cache(request: AddEventsRequest, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["system_admin", "admin"]:
        raise HTTPException(403, "Admin access required")
    if not request.event_ids:
        return {"message": "No event IDs provided", "added": 0}

    build_cache()
    return {"message": "Cache refreshed with new events", "total": len(_cache["result"])}

# ── Optional admin endpoints for polling control ──
@app.post("/enable-polling")
def enable_polling(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["system_admin", "admin"]:
        raise HTTPException(403, "Only admins can toggle polling")
    global _polling_enabled
    _polling_enabled = True
    return {"message": "Auto‑polling enabled"}

@app.post("/disable-polling")
def disable_polling(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["system_admin", "admin"]:
        raise HTTPException(403, "Only admins can toggle polling")
    global _polling_enabled
    _polling_enabled = False
    return {"message": "Auto‑polling disabled"}

@app.post("/force-update")
def force_update(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["system_admin", "admin"]:
        raise HTTPException(403, "Only admins can force update")
    process_new_events()
    return {"message": "Force update triggered"}

# ── Run the app ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.API.main:app", host="127.0.0.1", port=8000, reload=True)