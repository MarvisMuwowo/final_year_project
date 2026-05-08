import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import webbrowser
import threading

from auth      import auth_layout, register_auth_callbacks
from dashboard import dashboard_layout, register_dashboard_callbacks

# ── CSS ───────────────────────────────────────────────────────────────────────
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
</style>
"""

# ── APP ───────────────────────────────────────────────────────────────────────
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

# ── ROOT LAYOUT ───────────────────────────────────────────────────────────────
app.layout = html.Div([
    dcc.Location(id="url",          refresh=False),
    dcc.Store(id="auth-store",      storage_type="session"),
    dcc.Store(id="load-trigger",    data=0),
    html.Div(id="page-content")
])


# ── ROUTING ───────────────────────────────────────────────────────────────────
@app.callback(
    Output("page-content",  "children"),
    Output("load-trigger",  "data"),
    Input("url",            "pathname"),
    Input("auth-store",     "data"),
)
def display_page(pathname, auth_data):
    if auth_data and isinstance(auth_data, dict) and auth_data.get("token"):
        return dashboard_layout(
            auth_data["username"], auth_data["role"]
        ), 1
    return auth_layout, 0


# ── REGISTER ALL CALLBACKS ────────────────────────────────────────────────────
register_auth_callbacks(app)
register_dashboard_callbacks(app)


# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Security Log Prioritization Dashboard — CBU DICT")
    print("=" * 60)
    print("📡 Backend API : http://127.0.0.1:8000")
    print("🌐 Dashboard   : http://127.0.0.1:8050")
    print("⚠️  Make sure FastAPI is running on port 8000 first")
    print("=" * 60 + "\n")

    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8050")

    threading.Timer(1.5, open_browser).start()
    app.run(debug=True, port=8050, host="127.0.0.1")