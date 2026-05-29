# app/API/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'database'))
from config import DB_CONFIG

SECRET_KEY  = "cbu-dict-secret-key-2024"
ALGORITHM   = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ── Shared mutable cache — populated at startup by main.py ────────────────────
_cache = {
    "df_raw"            : None,
    "X_test"            : None,
    "result"            : None,
    "priority_counts"   : {},
    "shap_values"       : None,
    "explainer"         : None,
    "feature_importance": None,
}

# ── Shared model reference — set at startup by main.py ────────────────────────
_model_ref = {"model": None}

def get_cache():
    return _cache

def get_model():
    return _model_ref["model"]

def set_model(model):
    _model_ref["model"] = model


# ── DB helper ─────────────────────────────────────────────────────────────────
def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn

def get_user_from_db(username: str):
    conn   = None
    cursor = None
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, username, password_hash, role,
                   email, is_active, last_login
            FROM users WHERE username = %s
        """, (username,))
        return cursor.fetchone()
    except Exception as e:
        print(f"DB error: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# ── Auth dependency ───────────────────────────────────────────────────────────
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail      = "Could not validate credentials",
        headers     = {"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise credentials_exception

    user = get_user_from_db(username)
    if user is None:
        raise credentials_exception
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    return {
        "id"      : user["id"],
        "username": user["username"],
        "role"    : user["role"],
        "email"   : user["email"]
    }