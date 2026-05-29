from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
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

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'database'))
from config import DB_CONFIG

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'service'))
from preprocess import process_data

# ── Import shared dependencies ────────────────────────────────────────────────
from app.API.dependencies import (
    get_current_user, get_db_connection, get_user_from_db,
    _cache, set_model, SECRET_KEY, ALGORITHM
)

# ── Import routers ────────────────────────────────────────────────────────────
from app.API.classification import router as classification_router, init_feedback_table
from app.API.shap_explainer  import router as shap_router

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

# ── Load model ────────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'xgboost_model.pkl'
)
model = joblib.load(MODEL_PATH)
set_model(model)
print("Model loaded successfully")


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
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def create_access_token(data: dict):
    to_encode = data.copy()
    expire    = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ── Database init ─────────────────────────────────────────────────────────────
def init_database():
    conn   = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DO $$ BEGIN
                CREATE TYPE user_role AS ENUM
                    ('security_analyst', 'system_admin', 'admin', 'viewer');
            EXCEPTION
                WHEN duplicate_object THEN null;
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
        conn.commit()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


# ── Cache builder ─────────────────────────────────────────────────────────────
def get_events_df():
    conn = get_db_connection()
    df   = pd.read_sql("SELECT * FROM events", conn)
    conn.close()
    return df

def build_cache():
    print("\n── Building data cache ──")
    df = get_events_df()
    _, X_test, _, _ = process_data(df)

    behavioral_features = ["hour", "day_of_week", "is_weekend",
                           "computer", "user", "level", "keyword"]
    available    = [f for f in behavioral_features if f in X_test.columns]
    X_behavioral = X_test[available]

    iso        = IsolationForest(contamination=0.1, random_state=42)
    iso.fit(X_behavioral)
    raw_scores = iso.decision_function(X_behavioral)
    min_s      = raw_scores.min()
    max_s      = raw_scores.max()
    risk_score = 1 - (raw_scores - min_s) / (max_s - min_s)

    y_pred  = model.predict(X_test)
    result  = X_test.copy()
    result["predicted"]  = y_pred
    result["risk_score"] = risk_score
    result["priority"]   = pd.cut(
        risk_score,
        bins=[0, 0.33, 0.66, 1.0],
        labels=["Low", "Medium", "High"],
        include_lowest=True
    ).astype(str)

    priority_counts = result["priority"].value_counts().to_dict()

    print("  Computing SHAP values...")
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)

    feature_importance = dict(zip(
        model.get_booster().feature_names,
        model.feature_importances_.tolist()
    ))

    _cache["df_raw"]            = df
    _cache["X_test"]            = X_test
    _cache["result"]            = result
    _cache["priority_counts"]   = priority_counts
    _cache["shap_values"]       = shap_values
    _cache["explainer"]         = explainer
    _cache["feature_importance"]= feature_importance

    print(f"  High   : {priority_counts.get('High',   0)}")
    print(f"  Medium : {priority_counts.get('Medium', 0)}")
    print(f"  Low    : {priority_counts.get('Low',    0)}")
    print(f"  Total  : {len(result)}")
    print("── Cache ready ✓ ──\n")


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    init_database()
    init_feedback_table()
    build_cache()


# ── ROOT ──────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Windows Security Log Prioritization API is running"}


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_from_db(form_data.username)

    print(f"\n── Login ──")
    print(f"Username : {form_data.username}")
    print(f"Found    : {user is not None}")

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    match = verify_password(form_data.password, user["password_hash"])
    print(f"Password : {'✓' if match else '✗'}")

    if not match:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    conn = cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login = %s WHERE username = %s",
            (datetime.utcnow(), form_data.username)
        )
        conn.commit()
    except Exception as e:
        print(f"Error updating last_login: {e}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

    token = create_access_token(
        {"sub": user["username"], "role": user["role"]}
    )
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
        raise HTTPException(
            status_code=400,
            detail="Password too long — maximum 72 characters"
        )

    valid_roles = ["security_analyst", "system_admin", "admin", "viewer"]
    if user.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )

    conn = cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE username = %s", (user.username,)
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"Username '{user.username}' already exists"
            )

        cursor.execute(
            "SELECT id FROM users WHERE email = %s", (user.email,)
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"Email '{user.email}' already registered"
            )

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
        raise HTTPException(
            status_code=400,
            detail=f"Registration failed: {str(e)}"
        )
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ── ME ────────────────────────────────────────────────────────────────────────
@app.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    user = get_user_from_db(current_user["username"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id       =user["id"],
        username =user["username"],
        email    =user["email"],
        role     =user["role"],
        is_active=user["is_active"]
    )


# ── PROTECTED ENDPOINTS (require login) ───────────────────────────────────────
@app.get("/events")
def get_events(current_user: dict = Depends(get_current_user)):
    return _cache["df_raw"].to_dict(orient="records")


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
    return _cache["result"].to_dict(orient="records")


@app.get("/feature-importance")
def feature_importance(current_user: dict = Depends(get_current_user)):
    return _cache["feature_importance"]


@app.post("/refresh-cache")
def refresh_cache(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["system_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can refresh the cache"
        )
    build_cache()
    return {"message": "Cache refreshed", "total": len(_cache["result"])}


# ── SHAP ENDPOINT IS NOW HANDLED BY THE ROUTER ────────────────────────────────
# The /shap/event/{event_index} endpoint is in shap_explainer.py