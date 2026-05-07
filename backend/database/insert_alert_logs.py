"""
insert_alert_logs.py
--------------------
Loads a network-traffic CSV and inserts it into the `alert_logs` PostgreSQL table.

Requirements:
    pip install pandas psycopg2-binary python-dotenv

Usage:
    python insert_alert_logs.py --file path/to/data.csv

Environment variables (or .env file):
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import argparse
import hashlib
import ipaddress
import logging
import os
import re
from datetime import datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config / logging
# ---------------------------------------------------------------------------
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

BATCH_SIZE = 500          # rows per executemany batch
SEVERITY_ALLOWED = {"Low", "Medium", "High"}

# Internal RFC-1918 + loopback ranges used for source_is_internal detection
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_ip(ip: str) -> str:
    """SHA-256 of the IP string (hex digest) — one-way anonymisation."""
    return hashlib.sha256(ip.strip().encode()).hexdigest()


def is_internal(ip: str) -> bool | None:
    """Return True if the IP belongs to a private range, False if public, None on error."""
    try:
        addr = ipaddress.ip_address(ip.strip())
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        return None


def parse_timestamp(ts: str) -> datetime | None:
    ts = re.sub(r':\s+', ':', str(ts).strip())  # fix '16: 54: 00' → '16:54:00'
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d",
        "%y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    log.warning("Could not parse timestamp: %r", ts)
    return None


def clean_severity(val) -> str | None:
    """Normalise severity; fix the typo 'Mediun' → 'Medium' from the DDL."""
    if pd.isna(val):
        return None
    v = str(val).strip().capitalize()
    # DDL has a typo "Mediun" — map it to the corrected form
    if v in ("Mediun", "Medium"):
        return "Medium"
    return v if v in SEVERITY_ALLOWED else None


def safe_int(val) -> int | None:
    try:
        return int(float(val)) if not pd.isna(val) else None
    except (ValueError, TypeError):
        return None


def safe_float(val) -> float | None:
    try:
        return float(val) if not pd.isna(val) else None
    except (ValueError, TypeError):
        return None


def safe_str(val, max_len: int | None = None) -> str | None:
    if pd.isna(val):
        return None
    s = str(val).strip()
    if max_len:
        s = s[:max_len]
    return s or None


# ---------------------------------------------------------------------------
# Row transformer
# ---------------------------------------------------------------------------

def transform_row(row: pd.Series) -> tuple:
    """
    Map a raw CSV row → a tuple matching the INSERT column order below.

    Column order in INSERT:
        event_timestamp, protocol, source_port, packet_length,
        source_ip_hash, destination_ip_hash,
        source_is_internal, destination_is_internal,
        traffic_type, attack_type, attack_signature,
        anomaly_score, malware_indicator,
        severity_level, log_source, network_segment
    """
    # NOTE: The dataset schema shared has no Source.IP.Address column (column index 1
    # was omitted from the info block). We hash Destination.IP.Address for both hashes
    # and leave source_ip_hash as a placeholder hash.  If your CSV does contain a
    # source IP column, replace `src_ip` below with row["Source.IP.Address"].
    dest_ip  = safe_str(row.get("Destination.IP.Address", ""))
    src_ip   = safe_str(row.get("Source.IP.Address", dest_ip or ""))  # fallback

    return (
        parse_timestamp(row["Timestamp"]),                  # event_timestamp
        safe_str(row["Protocol"], 20),                      # protocol
        safe_int(row["Source.Port"]),                       # source_port
        safe_int(row["Packet.Length"]),                     # packet_length
        hash_ip(src_ip)  if src_ip  else "unknown",         # source_ip_hash
        hash_ip(dest_ip) if dest_ip else "unknown",         # destination_ip_hash
        is_internal(src_ip)  if src_ip  else None,          # source_is_internal
        is_internal(dest_ip) if dest_ip else None,          # destination_is_internal
        safe_str(row["Traffic.Type"], 50),                  # traffic_type
        safe_str(row["Attack.Type"], 100),                  # attack_type
        safe_str(row["Attack.Signature"]),                  # attack_signature
        safe_float(row["Anomaly.Scores"]),                  # anomaly_score
        safe_str(row["Malware.Indicators"]),                # malware_indicator
        clean_severity(row["Severity.Level"]),              # severity_level
        safe_str(row["Log.Source"], 50),                    # log_source
        safe_str(row["Network.Segment"], 100),              # network_segment
    )


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

INSERT_SQL = """
INSERT INTO alert_logs (
    event_timestamp, protocol, source_port, packet_length,
    source_ip_hash, destination_ip_hash,
    source_is_internal, destination_is_internal,
    traffic_type, attack_type, attack_signature,
    anomaly_score, malware_indicator,
    severity_level, log_source, network_segment
) VALUES (
    %s, %s, %s, %s,
    %s, %s,
    %s, %s,
    %s, %s, %s,
    %s, %s,
    %s, %s, %s
)
"""


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "malware_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "test1234"),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_and_insert(csv_path: str) -> None:
    log.info("Reading CSV: %s", csv_path)
    df = pd.read_csv(csv_path)
    log.info("Loaded %d rows, %d columns", len(df), len(df.columns))

    # Normalise column names: strip whitespace
    df.columns = df.columns.str.strip()

    rows_ok, rows_err = 0, 0
    batch: list[tuple] = []

    conn = get_connection()
    cur = conn.cursor()
    log.info("Connected to database — starting insert …")

    for idx, row in df.iterrows():
        try:
            batch.append(transform_row(row))
        except Exception as exc:
            log.warning("Row %d skipped — transform error: %s", idx, exc)
            rows_err += 1
            continue

        if len(batch) >= BATCH_SIZE:
            try:
                execute_batch(cur, INSERT_SQL, batch)
                conn.commit()
                rows_ok += len(batch)
                log.info("Inserted %d rows (total so far: %d)", len(batch), rows_ok)
            except Exception as exc:
                conn.rollback()
                log.error("Batch insert failed: %s — rolling back batch", exc)
                rows_err += len(batch)
            batch = []

    # Flush remainder
    if batch:
        try:
            execute_batch(cur, INSERT_SQL, batch)
            conn.commit()
            rows_ok += len(batch)
        except Exception as exc:
            conn.rollback()
            log.error("Final batch insert failed: %s", exc)
            rows_err += len(batch)

    cur.close()
    conn.close()

    log.info("Done — inserted: %d  |  skipped/errored: %d", rows_ok, rows_err)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Insert alert log CSV into PostgreSQL.")
    parser.add_argument("--file", default=r"C:\Users\WamutoGeneralDealers\Desktop\ML project\backend\data\malware_clean_dataset.csv", help="Path to the CSV file")
    args = parser.parse_args()
    load_and_insert(args.file)