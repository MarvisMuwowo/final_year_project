# utils.py
import plotly.graph_objects as go

API = "http://127.0.0.1:8000"

CLASS_LABELS = {
    0: "Auditing settings on object were changed.",
    1: "Logon",
    2: "Other",
    3: "Special Logon",
    4: "User Account Management",
}

def get_headers(auth_data):
    if auth_data and isinstance(auth_data, dict) and auth_data.get("token"):
        return {"Authorization": f"Bearer {auth_data['token']}"}
    return {}

def empty_fig():
    return go.Figure().update_layout(
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font_color="white"
    )