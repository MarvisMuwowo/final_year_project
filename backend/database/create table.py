import psycopg2
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database'))
from config import DB_CONFIG


conn = psycopg2.connect(**DB_CONFIG)
conn.autocommit = True
cursor = conn.cursor()

# ── Step 1: Drop both possible table names cleanly
cursor.execute("DROP TABLE IF EXISTS events CASCADE")
cursor.execute("DROP TABLE IF EXISTS event CASCADE")
print("Old tables dropped")

# ── Step 2: Create fresh table
cursor.execute("""
    CREATE TABLE events (
        id            SERIAL PRIMARY KEY,
        event_id      INTEGER      NOT NULL,
        logged        TIMESTAMP    NOT NULL,
        level         VARCHAR(50),
        "user"        VARCHAR(255),
        log_name      VARCHAR(100),
        opcode        VARCHAR(50),
        task_category TEXT,
        computer      VARCHAR(255),
        keyword       VARCHAR(50)
        
    )
""")
print("Table created")

# ── Step 3: Create indexes one by one
cursor.execute("CREATE INDEX idx_event_id      ON events (event_id)")
print("Index 1 done")

cursor.execute("CREATE INDEX idx_logged        ON events (logged)")
print("Index 2 done")

cursor.execute("CREATE INDEX idx_computer      ON events (computer)")
print("Index 3 done")

cursor.execute("CREATE INDEX idx_level         ON events (level)")
print("Index 4 done")

cursor.execute("CREATE INDEX idx_keyword       ON events (keyword)")
print("Index 5 done")

cursor.execute("CREATE INDEX idx_task_category ON events (task_category)")
print("Index 6 done")

# ── Step 4: Verify
cursor.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'events'
    ORDER BY ordinal_position
""")
print("\n── Table columns ──")
for row in cursor.fetchall():
    print(f"  {row[0]:<20} {row[1]}")

cursor.close()
conn.close()
print("\nDone ✓")

