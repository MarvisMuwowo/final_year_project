import psycopg2
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database'))
from config import DB_CONFIG

# ── Load CSV ──────────────────────────────────────────────────────────────────
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'local_event_logs.csv')
df = pd.read_csv(CSV_PATH)
print(f"Loaded {len(df)} rows from CSV")

# ── Clean data ────────────────────────────────────────────────────────────────
# Convert logged to datetime, invalid values become NaT
df["logged"] = pd.to_datetime(df["logged"], errors="coerce")

# Drop rows where logged is NaT — can't insert NULL into NOT NULL column
df = df.dropna(subset=["logged"])

# Replace NaN strings in other columns with None (PostgreSQL NULL)
df = df.where(pd.notnull(df), None)

print(f"Clean rows to insert: {len(df)}")

# ── Connect to PostgreSQL ─────────────────────────────────────────────────────
conn = psycopg2.connect(**DB_CONFIG)
conn.autocommit = True
cursor = conn.cursor()

# ── Insert rows ───────────────────────────────────────────────────────────────
inserted = 0
skipped  = 0

for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO events
            (event_id, logged, level, "user", log_name, opcode, task_category, computer, keyword)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
       
    """, (
        row["event_id"],
        row["logged"],
        row["level"],
        row["user"],
        row["log_name"],
        row["opcode"],
        row["task_category"],
        row["computer"],
        row["keyword"],
    ))

    if cursor.rowcount > 0:
        inserted += 1
    else:
        skipped += 1

cursor.close()
conn.close()

print(f"Inserted : {inserted}")
print(f"Skipped  : {skipped} (duplicates)")
print("Done ✓")