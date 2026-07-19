import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import webbrowser
import threading

from auth      import auth_layout,      register_auth_callbacks
from dashboard import dashboard_layout,  register_dashboard_callbacks
from landing   import landing_layout,    register_landing_callbacks   # ← new

custom_css = """
<style>
    body {
        background-color: #0f172a;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0; padding: 0;
    }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #3b82f6; border-radius: 10px; }
    a { transition: opacity 0.2s; }
    a:hover { opacity: 0.8; }
</style>
"""

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="SecureLog AI — CBU DICT",
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

app.layout = html.Div([
    dcc.Location(id="url",          refresh=False),
    dcc.Store(id="auth-store",      storage_type="session"),
    dcc.Store(id="auth-mode",       data="login"),
    dcc.Store(id="load-trigger",    data=0),
    dcc.Interval(id="auto-refresh", interval=30*1000, n_intervals=0),
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
    # ── /dashboard or / when logged in → dashboard
    if pathname == "/dashboard":
        if auth_data and isinstance(auth_data, dict) and auth_data.get("token"):
            return dashboard_layout(
                auth_data["username"], auth_data["role"]
            ), 1
        else:
            # not logged in → auth page
            return auth_layout, 0

    # ── /login → auth page directly
    if pathname == "/login":
        return auth_layout, 0

    # ── / → landing page
    return landing_layout, 0


# ── REGISTER CALLBACKS ────────────────────────────────────────────────────────
register_landing_callbacks(app)
register_auth_callbacks(app)
register_dashboard_callbacks(app)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 SecureLog AI — CBU DICT")
    print("=" * 60)
    print("🌐 Landing page : http://127.0.0.1:8050")
    print("📊 Dashboard    : http://127.0.0.1:8050/dashboard")
    print("📡 Backend API  : http://127.0.0.1:8000")
    print("📖 API Docs     : http://127.0.0.1:8000/docs")
    print("=" * 60 + "\n")

    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8050")

    threading.Timer(1.5, open_browser).start()
    app.run(debug=True, port=8050, host="127.0.0.1")