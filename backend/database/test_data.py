import pandas as pd
import os

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'local_event_logs.csv')
df = pd.read_csv(CSV_PATH)

print("── First 5 rows ──")
print(df.head().to_string())

print("\n── logged column sample ──")
print(df["logged"].head(20).to_string())

print("\n── Data types ──")
print(df.dtypes)

print("\n── Null counts ──")
print(df.isnull().sum())