# backend/app/API/classification.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'database'))
from config import DB_CONFIG

from app.API.dependencies import get_current_user, get_db_connection, get_cache

router = APIRouter(prefix="/classification", tags=["Classification Feedback"])

# ── Pydantic Models ───────────────────────────────────────────────────────────
class FeedbackSubmit(BaseModel):
    event_index: int
    event_id: int
    predicted_class: int
    predicted_label: str
    correct_label: str
    analyst_comment: str = ""
    is_correctly_classified: bool

class FeedbackResponse(BaseModel):
    feedback_id: int
    message: str

class FeedbackHistory(BaseModel):
    id: int
    event_index: int
    event_id: int
    predicted_label: str
    correct_label: str
    is_correctly_classified: bool
    analyst_comment: str
    analyst_username: str
    submitted_at: str
    status: str


# ── Database Functions ─────────────────────────────────────────────────────────
def init_feedback_table():
    """Initialize the feedback table in database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classification_feedback (
                id SERIAL PRIMARY KEY,
                event_index INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                predicted_class INTEGER NOT NULL,
                predicted_label VARCHAR(255) NOT NULL,
                correct_label VARCHAR(255) NOT NULL,
                analyst_comment TEXT,
                is_correctly_classified BOOLEAN NOT NULL,
                analyst_username VARCHAR(50) NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending',
                reviewed_by VARCHAR(50),
                reviewed_at TIMESTAMP,
                admin_comment TEXT
            )
        """)
        conn.commit()
        print("Feedback table initialized")
    except Exception as e:
        print(f"Feedback table init error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(
    feedback: FeedbackSubmit,
    current_user: dict = Depends(get_current_user)
):
    """Submit feedback for a classified event"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO classification_feedback 
            (event_index, event_id, predicted_class, predicted_label, 
             correct_label, analyst_comment, is_correctly_classified, 
             analyst_username, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            feedback.event_index,
            feedback.event_id,
            feedback.predicted_class,
            feedback.predicted_label,
            feedback.correct_label,
            feedback.analyst_comment,
            feedback.is_correctly_classified,
            current_user["username"],
            "pending"
        ))
        
        conn.commit()
        feedback_id = cursor.fetchone()[0]
        
        return FeedbackResponse(
            feedback_id=feedback_id,
            message="Feedback submitted successfully"
        )
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


@router.get("/event/{event_index}")
def get_event_classification(
    event_index: int,
    current_user: dict = Depends(get_current_user)
):
    """Get classification details for a specific event"""
    cache = get_cache()
    result = cache.get("result")
    
    if result is None:
        raise HTTPException(503, "Cache not ready")
    
    if event_index >= len(result):
        raise HTTPException(404, f"Event {event_index} not found")
    
    event_data = result.iloc[event_index]
    
    return {
        "event_index": event_index,
        "event_id": int(event_data.get("event_id", event_index)) if "event_id" in event_data else event_index,
        "predicted_class": int(event_data.get("predicted", 0)),
        "predicted_label": "Unknown",
        "priority": event_data.get("priority", "Low"),
        "risk_score": float(event_data.get("risk_score", 0.5))
    }


@router.get("/feedback/all")
def get_all_feedback(
    current_user: dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
):
    """Get all feedback submissions (admin only)"""
    # Check if user is admin
    if current_user["role"] not in ["admin", "system_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT id, event_index, event_id, predicted_label, correct_label,
                   is_correctly_classified, analyst_comment, analyst_username,
                   submitted_at, status
            FROM classification_feedback
            ORDER BY submitted_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        feedback_list = cursor.fetchall()
        
        # Convert datetime to string
        for item in feedback_list:
            if item.get("submitted_at"):
                item["submitted_at"] = item["submitted_at"].strftime("%Y-%m-%d %H:%M:%S")
        
        return feedback_list
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch feedback: {str(e)}"
        )
    finally:
        cursor.close()
        conn.close()


@router.get("/feedback/{feedback_id}")
def get_feedback_by_id(
    feedback_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get specific feedback by ID"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT id, event_index, event_id, predicted_label, correct_label,
                   is_correctly_classified, analyst_comment, analyst_username,
                   submitted_at, status, reviewed_by, reviewed_at, admin_comment
            FROM classification_feedback
            WHERE id = %s
        """, (feedback_id,))
        
        feedback = cursor.fetchone()
        
        if not feedback:
            raise HTTPException(404, "Feedback not found")
        
        if feedback.get("submitted_at"):
            feedback["submitted_at"] = feedback["submitted_at"].strftime("%Y-%m-%d %H:%M:%S")
        if feedback.get("reviewed_at"):
            feedback["reviewed_at"] = feedback["reviewed_at"].strftime("%Y-%m-%d %H:%M:%S")
        
        return feedback
        
    finally:
        cursor.close()
        conn.close()


@router.put("/feedback/{feedback_id}/review")
def review_feedback(
    feedback_id: int,
    status: str,
    admin_comment: str = "",
    current_user: dict = Depends(get_current_user)
):
    """Review feedback (admin only)"""
    if current_user["role"] not in ["admin", "system_admin"]:
        raise HTTPException(403, "Admin access required")
    
    if status not in ["pending", "reviewed", "rejected"]:
        raise HTTPException(400, "Invalid status")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE classification_feedback
            SET status = %s, reviewed_by = %s, reviewed_at = %s, admin_comment = %s
            WHERE id = %s
            RETURNING id
        """, (status, current_user["username"], datetime.utcnow(), admin_comment, feedback_id))
        
        if cursor.fetchone() is None:
            raise HTTPException(404, "Feedback not found")
        
        conn.commit()
        
        return {"message": f"Feedback {feedback_id} updated to {status}"}
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Failed to review feedback: {str(e)}")
    finally:
        cursor.close()
        conn.close()