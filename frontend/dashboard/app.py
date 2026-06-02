import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import webbrowser
import threading

# Import the modular layouts and callbacks
from auth import auth_layout, register_auth_callbacks
from dashboard import dashboard_layout, register_dashboard_callbacks

# ── Custom CSS (consistent with professional dark theme) ──────────────────────
custom_css = """
<style>
    body {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        min-height: 100vh;
    }
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #1a1a2e; }
    ::-webkit-scrollbar-thumb { background: #3b82f6; border-radius: 10px; }
    .card {
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.2) !important;
    }
</style>
"""

# ── Dash App Initialisation ──────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="Security Log Prioritization — CBU DICT",
    suppress_callback_exceptions=True
)

app.index_string = f'''
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
        {custom_css}
        <link rel="stylesheet"
              href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>
'''

# ── Root Layout ──────────────────────────────────────────────────────────────
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="auth-store", storage_type="session"),   # stores user token
    dcc.Store(id="auth-mode", data="login"),              # tracks login/register mode
    dcc.Store(id="load-trigger", data=0),                 # triggers initial data fetch
    html.Div(id="page-content")
])

# ── Routing: Show dashboard if logged in, else show auth page ────────────────
@app.callback(
    Output("page-content", "children"),
    Output("load-trigger", "data"),
    Input("url", "pathname"),
    Input("auth-store", "data"),
)
def display_page(pathname, auth_data):
    if auth_data and isinstance(auth_data, dict) and auth_data.get("token"):
        # User is authenticated → show dashboard
        return dashboard_layout(
            auth_data.get("username", "Analyst"),
            auth_data.get("role", "security_analyst")
        ), 1
    # Not logged in → show authentication page
    return auth_layout, 0

# ── Register all callbacks from auth and dashboard modules ───────────────────
register_auth_callbacks(app)
register_dashboard_callbacks(app)

# ── Run the server ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" Security Log Prioritization Dashboard — CBU DICT")
    print("=" * 60)
    print("📡 Backend API : http://127.0.0.1:8000")
    print("🌐 Dashboard   : http://127.0.0.1:8050")
    print("=" * 60 + "\n")

    # Automatically open the browser after a short delay
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8050")

    threading.Timer(1.5, open_browser).start()
    app.run(debug=True, port=8050, host="127.0.0.1")