import random
import pandas as pd
from datetime import datetime, timedelta

# Event mapping
event_map = {
    4624: ("Logon", "Audit Success"),
    4672: ("Special Logon", "Audit Success"),
    5379: ("User Account Management", "Audit Success")
}

data = []

for i in range(1000):
    event_id = random.choice(list(event_map.keys()))
    
    # Create clickable hyperlink in Excel CSV
    hyperlink = f'=HYPERLINK("https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-{event_id}", "Event Log Online Help")'
    
    event = {
        "LogName": "Security",
        "Source": "Microsoft Windows security",
        "EventID": event_id,
        "Level": "Information",
        "User": "N/A",
        "Opcode": "Info",
        "TaskCategory": event_map[event_id][0],
        "Keywords": event_map[event_id][1],
        "Logged": datetime.now() - timedelta(minutes=random.randint(0, 10000)),
        "Computer": f"PC-{random.randint(1,5)}",
        "MoreInformation": hyperlink  # ✅ clickable in Excel
    }
    
    data.append(event)

df = pd.DataFrame(data)

# Sort by Logged time
df = df.sort_values(by="Logged")

# Format timestamp
df["Logged"] = df["Logged"].dt.strftime("%Y-%m-%d %H:%M:%S")

# Save CSV (Excel will interpret HYPERLINK)
df.to_csv("windows_security_logs.csv", index=False, quoting=1)  # quoting=1 = QUOTE_ALL

print("dataset generated successfully!")