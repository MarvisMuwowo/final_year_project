import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
import logging
import sys

#  Logging setup 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

#  Database configuration 
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "windows_security_log_db",   # ← change
    "user":     "postgres",   # ← change
    "password": "test1234",   # ← change
}

# CSV path 
CSV_PATH = r"C:\Users\WamutoGeneralDealers\Desktop\ML_project\backend\data\local_event_logs.csv"

# ── Column mapping ──
# Map CSV column names → events table columns.
# Adjust the keys to match the actual headers in your CSV file.
COLUMN_MAP = {
    "Keywords":      "keyword",       # CSV col  →  table col
    "Date and Time":        "logged",
    "Source":        "source",
    "Event ID":      "event_id",
    "Task Category": "task_category",
}

#  Batch size (rows sent to Postgres per round-trip) 
BATCH_SIZE = 500


def load_csv(path: str) -> pd.DataFrame:
    """Read the CSV and return a cleaned DataFrame."""
    log.info(f"Reading CSV: {path}")
    df = pd.read_csv(path)
    log.info(f"  Rows loaded : {len(df):,}")
    log.info(f"  Columns     : {list(df.columns)}")

    # Rename columns according to COLUMN_MAP (only renames if key != value)
    rename = {k: v for k, v in COLUMN_MAP.items() if k != v and k in df.columns}
    if rename:
        df.rename(columns=rename, inplace=True)
        log.info(f"  Renamed columns: {rename}")

    # Keep only the columns we need
    required = list(COLUMN_MAP.values())
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"The following columns are missing from the CSV: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )
    df = df[required].copy()

    # Basic cleaning
    df.dropna(subset=required, inplace=True)         # drop rows with any NULL in required cols
    df["event_id"] = df["event_id"].astype(int)      # ensure integer
    df["logged"]   = pd.to_datetime(df["logged"])    # ensure datetime

    log.info(f"  Rows after cleaning: {len(df):,}")
    return df


def insert_data(df: pd.DataFrame, db_config: dict) -> None:
    """Insert DataFrame rows into the events table using execute_batch."""
    INSERT_SQL = """
        INSERT INTO events (keyword, logged, source, event_id, task_category)
        VALUES (%(keyword)s, %(logged)s, %(source)s, %(event_id)s, %(task_category)s)
  """

    records = df.to_dict(orient="records")

    log.info("Connecting to the database …")
    conn = psycopg2.connect(**db_config)
    #conn.commit()    
    try:
        with conn:                          # auto-commit on success, rollback on error
            with conn.cursor() as cur:
                log.info(f"Inserting {len(records):,} rows in batches of {BATCH_SIZE} …")
                execute_batch(cur, INSERT_SQL, records, page_size=BATCH_SIZE)
                log.info(f"Done. Rows affected (approx): {cur.rowcount}")
    finally:
        conn.close()
        log.info("Database connection closed.")


def main():
    df = load_csv(CSV_PATH)
    insert_data(df, DB_CONFIG)
    log.info("✅ Import complete.")


if __name__ == "__main__":
    main()
