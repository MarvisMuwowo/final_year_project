# backend/app/service/collecting_events.py
import os
import sys
import requests
import psycopg2
from datetime import datetime, timedelta
import logging
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database')))
from config import DB_CONFIG

# ── Logging (UTF-8 safe) ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("event_collector.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_BASE = "http://127.0.0.1:8000"
ADMIN_USERNAME = "mary"       
ADMIN_PASSWORD = "123456"    

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def read_security_log(last_minutes=5):
    try:
        import win32evtlog
    except ImportError:
        logger.error("pywin32 not installed. Run: pip install pywin32")
        return []

    server = '.'
    log_type = 'Security'
    try:
        hand = win32evtlog.OpenEventLog(server, log_type)
        logger.info("Opened Security log")
    except Exception as e:
        logger.error(f"Failed to open Security log: {e}")
        return []

    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
    events = []
    cutoff_time = datetime.now() - timedelta(minutes=last_minutes)

    try:
        total = win32evtlog.GetNumberOfEventLogRecords(hand)
        logger.info(f"Total records in Security log: {total}")
    except Exception as e:
        logger.error(f"Failed to get record count: {e}")
        win32evtlog.CloseEventLog(hand)
        return []

    if total == 0:
        logger.warning("Security log is empty. Enable auditing.")
        win32evtlog.CloseEventLog(hand)
        return []

    try:
        events_read = win32evtlog.ReadEventLog(hand, flags, 0)
    except Exception as e:
        logger.error(f"Failed to read events: {e}")
        win32evtlog.CloseEventLog(hand)
        return []

    for event in events_read:
        try:
            event_time = datetime.fromtimestamp(event.TimeGenerated)
        except:
            event_time = datetime.now()

        if event_time < cutoff_time:
            continue

        event_dict = {
            "event_id": event.EventID,
            "logged": event_time.strftime("%Y-%m-%d %H:%M:%S"),
            "level": "Information",
            "user": "",
            "log_name": "Security",
            "opcode": "",
            "computer": "",
            "keyword": "",
            "task_category": ""
        }

        try:
            if hasattr(event, 'StringInserts') and event.StringInserts:
                for s in event.StringInserts:
                    if "Account Name:" in s:
                        parts = s.split(":")
                        if len(parts) > 1:
                            event_dict["user"] = parts[1].strip()
                    elif "Computer:" in s or "Computer Name:" in s:
                        parts = s.split(":")
                        if len(parts) > 1:
                            event_dict["computer"] = parts[1].strip()
        except:
            pass

        # Map task category
        eid = event.EventID
        if eid == 4624 or eid == 4625:
            event_dict["task_category"] = "Logon"
        elif eid == 4672:
            event_dict["task_category"] = "Special Logon"
        elif eid in [4720, 4722, 4723, 4724, 4725, 4726, 4730, 4731, 4732, 4733, 4734, 4735, 4737, 4738, 4740]:
            event_dict["task_category"] = "User Account Management"
        elif eid in [4656, 4657, 4658, 4659, 4660, 4661, 4662, 4663, 4664, 4665, 4666, 4667, 4668]:
            event_dict["task_category"] = "Auditing settings on object were changed."
        else:
            event_dict["task_category"] = "Other"

        events.append(event_dict)

    win32evtlog.CloseEventLog(hand)
    logger.info(f"Collected {len(events)} events from last {last_minutes} minutes")
    return events

def insert_events_to_db(events):
    if not events:
        return []

    conn = get_db_connection()
    cursor = conn.cursor()
    inserted_ids = []

    for ev in events:
        try:
            # Check duplicate
            cursor.execute(
                "SELECT id FROM events WHERE event_id = %s AND logged = %s",
                (ev["event_id"], ev["logged"])
            )
            if cursor.fetchone():
                continue

            # Insert with quoted "user" (reserved keyword)
            cursor.execute("""
                INSERT INTO events 
                (event_id, logged, level, "user", log_name, opcode, computer, keyword, task_category)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                ev["event_id"], ev["logged"], ev["level"], ev["user"],
                ev["log_name"], ev["opcode"], ev["computer"],
                ev["keyword"], ev["task_category"]
            ))
            row = cursor.fetchone()
            inserted_ids.append(row[0])
        except Exception as e:
            logger.error(f"Insert error for event {ev['event_id']}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    logger.info(f"Inserted {len(inserted_ids)} new events")
    return inserted_ids

def get_admin_token():
    try:
        resp = requests.post(
            f"{API_BASE}/login",
            data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
        else:
            logger.error(f"Login failed: {resp.status_code} - {resp.text}")
            return None
    except requests.exceptions.ConnectionError:
        logger.warning("FastAPI server not running. Events inserted but cache will be updated by scheduler.")
        return None
    except Exception as e:
        logger.error(f"Login request failed: {e}")
        return None

def trigger_add_events(event_ids):
    if not event_ids:
        return True
    token = get_admin_token()
    if not token:
        logger.info("Skipping cache update (API not available or login failed). Scheduler will pick up events.")
        return False
    try:
        resp = requests.post(
            f"{API_BASE}/add-events",
            headers={"Authorization": f"Bearer {token}"},
            json={"event_ids": event_ids},
            timeout=30
        )
        if resp.status_code == 200:
            logger.info(f"Added {resp.json().get('added', 0)} events to cache")
            return True
        else:
            logger.error(f"Failed to add events: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Could not reach API: {e}")
        return False

if __name__ == "__main__":
    logger.info("Collecting Windows Security Events")
    try:
        events = read_security_log(last_minutes=5)
        if not events:
            logger.info("No events found in last 5 minutes.")
            sys.exit(0)

        inserted_ids = insert_events_to_db(events)
        if not inserted_ids:
            logger.info("No new events inserted (all duplicates).")
            sys.exit(0)

        # Try to update cache (optional; scheduler will handle if fails)
        trigger_add_events(inserted_ids)
        logger.info(f"Processed {len(inserted_ids)} new events.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)