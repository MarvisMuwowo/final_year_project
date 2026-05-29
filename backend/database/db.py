import psycopg2
from config import DB_CONFIG
import pandas as pd

# Print config to verify settings
print(DB_CONFIG)

# Establish connection
try:
    conn = psycopg2.connect(**DB_CONFIG)
    print("Connected successfully")
except Exception as e:
    print("Connection failed:", e)
    conn = None

# Define function to fetch events
def get_events(connection):
    query = "SELECT * FROM users LIMIT 10"
    return pd.read_sql(query, connection)

# Call the function and display results
if conn:
    df = get_events(conn)
    print(df)
    conn.close()
   