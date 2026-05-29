import win32evtlog
import win32evtlogutil
import win32security
import pywintypes
import pandas as pd
from datetime import datetime
import os


# ── 1. RESOLVE HELPERS ──
def resolve_level(event_type):
    mapping = {
        win32evtlog.EVENTLOG_INFORMATION_TYPE : "Information",
        win32evtlog.EVENTLOG_WARNING_TYPE     : "Warning",
        win32evtlog.EVENTLOG_ERROR_TYPE       : "Error",
        win32evtlog.EVENTLOG_AUDIT_SUCCESS    : "Audit Success",
        win32evtlog.EVENTLOG_AUDIT_FAILURE    : "Information",
    }
    return mapping.get(event_type, "Information")



def resolve_keyword(event_type):
    mapping = {
        win32evtlog.EVENTLOG_AUDIT_SUCCESS    : "Audit Success",
        win32evtlog.EVENTLOG_AUDIT_FAILURE    : "Audit Failure",
        win32evtlog.EVENTLOG_INFORMATION_TYPE : "Classic",
        win32evtlog.EVENTLOG_WARNING_TYPE     : "Classic",
        win32evtlog.EVENTLOG_ERROR_TYPE       : "Classic",
    }
    return mapping.get(event_type, "Unknown")


def resolve_opcode(event_type):
    mapping = {
        win32evtlog.EVENTLOG_INFORMATION_TYPE : "Info",
        win32evtlog.EVENTLOG_WARNING_TYPE     : "Info",
        win32evtlog.EVENTLOG_ERROR_TYPE       : "Info",
        win32evtlog.EVENTLOG_AUDIT_SUCCESS    : "Info",
        win32evtlog.EVENTLOG_AUDIT_FAILURE    : "Info",
    }
    return mapping.get(event_type, "Info")


def resolve_task_category(event, log_name):
    try:
        categories = {
            12544:"Logon",
            12548:"Special Logon",
            13824:"User Account Management",
            12545:"Logoff",
            12546:"Account Lockout",
            13569:"Registry",
            13575:"File Share",
            13573:"Application Generated"
        }

        if event.EventCategory in categories:
            return categories[event.EventCategory]
        
        msg=win32evtlogutil.SafeFormatMessage(event,log_name)
        first_line=msg.split("\n")[0].strip()
        return first_line if first_line else str(event.EventCategory)
    except Exception:
        return str(event.EventCategory) if event.EventCategory else "N/A"

def resolve_timestamp(event):
    try:
        # TimeGenerated is a pywintypes.datetime object — convert directly
        t = event.TimeGenerated
        return datetime(t.year, t.month, t.day, t.hour, t.minute, t.second)
    except Exception as e:
        print(f"  Timestamp error: {e}")
        return None


def resolve_user(event):
    try:
        sid = event.Sid
        if sid:
            name, domain, _ = win32security.LookupAccountSid(None, sid)
            return f"{domain}\\{name}"
        # If no SID, return the source name as fallback
        return "N/A"
    except Exception:
        return "N/A"

# ── 2. COLLECT EVENTS FROM ONE LOG 
def get_event_logs(log_name="Security", max_events=25000):
    """
    Read events from Windows Event Viewer and return as a DataFrame.
    """
    server = None
    hand   = win32evtlog.OpenEventLog(server, log_name)
    flags  = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

    records = []
    total   = 0

    print(f"\n── Collecting [{log_name}] ──")

    while True:
        try:
            events = win32evtlog.ReadEventLog(hand, flags, 0)
        except pywintypes.error as e:
            print(f"  Read error: {e}")
            break

        if not events:
            break

        for event in events:
            records.append({
                "event_id"      : event.EventID & 0xFFFF,
                "logged"        : resolve_timestamp(event),
                "level"         : resolve_level(event.EventType),
                "user"          : resolve_user(event),
                "log_name"      : log_name,
                "opcode"        : resolve_opcode(event.EventType),
                "task_category" : resolve_task_category(event, log_name),
                "computer"      : str(event.ComputerName) if event.ComputerName else "N/A",
                "keyword"       : resolve_keyword(event.EventType),
            })

            total += 1
            if total % 1000 == 0:
                print(f"  Progress: {total} events collected...")

            if total >= max_events:
                break

        if total >= max_events:
            break

    win32evtlog.CloseEventLog(hand)
    print(f"  Done — {total} events collected from [{log_name}]")
    return pd.DataFrame(records)


# # ── 3. COLLECT FROM ALL LOGS 
# def collect_all_logs(max_events_per_log=20000):
#     """Collect from Security, Application and System logs and combine."""
#     logs   = ["Security", "Application", "System"]
#     frames = []

#     for log in logs:
#         try:
#             df = get_event_logs(log_name=log, max_events=max_events_per_log)
#             frames.append(df)
#         except Exception as e:
#             print(f"  Could not read [{log}]: {e}")

#     combined = pd.concat(frames, ignore_index=True)
#     return combined


# ── 4. SAVE TO CSV ────────────────────────────────────────────────────────────
def save_to_csv(df, path):
    """
    Save collected events to CSV.
    - First run  → creates the file
    - Next runs  → appends and removes duplicates automatically
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        existing    = pd.read_csv(path)
        combined    = pd.concat([existing, df], ignore_index=True)
        combined    = combined.drop_duplicates(
                          subset=["event_id", "logged", "computer"]
                      )
        combined.to_csv(path, index=False, encoding="utf-8")
        new_rows = len(combined) - len(existing)
        print(f"\n── CSV Updated ──")
        print(f"  Existing rows : {len(existing)}")
        print(f"  New rows added: {new_rows}")
        print(f"  Total rows    : {len(combined)}")
    else:
        df.to_csv(path, index=False, encoding="utf-8")
        print(f"\n── CSV Created ──")
        print(f"  Total rows    : {len(df)}")

    print(f"  Saved to      : {os.path.abspath(path)}")


# ── 5. PREVIEW ─
def preview(df):
    print("\n── Preview (first 5 rows) ──")
    print(df.head().to_string())
    print(f"\n── Summary ──")
    print(f"Total events     : {len(df)}")
    print(f"\nBy log_name:\n{df['log_name'].value_counts().to_string()}")
    print(f"\nBy level:\n{df['level'].value_counts().to_string()}")
    print(f"\nBy keyword:\n{df['keyword'].value_counts().to_string()}")
    print(f"\nTop event IDs:\n{df['event_id'].value_counts().head(10).to_string()}")
    print(f"\nTop computers:\n{df['computer'].value_counts().head(5).to_string()}")


# ── ENTRY POINT ─────
if __name__ == "__main__":

    # Path to your existing data folder
    CSV_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "data", "local_event_logs.csv"
    )

    # Step 1 — collect Security logs only
    df = get_event_logs(log_name="Security", max_events=25000)

       

    print(f"\n── Filtered Results ──")
    print(f"Total events after filter : {len(df)}")
    print(f"\nBy event_id:\n{df['event_id'].value_counts().to_string()}")

    # Step 3 — preview
    preview(df)

    # Step 4 — save to CSV
    save_to_csv(df, path=CSV_PATH)

    print("\nDone ✓")