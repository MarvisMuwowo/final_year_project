import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import requests
import pandas as pd
import webbrowser
import threading

API = "http://127.0.0.1:8000"

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    title="Security Log Prioritization",
    suppress_callback_exceptions=True
)

custom_css = """
<style>
    body {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        min-height: 100vh;
    }
    .custom-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #3b82f6;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }
    .login-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 2px solid #3b82f6;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }
    .custom-input {
        background-color: #0f172a !important;
        border: 2px solid #3b82f6 !important;
        color: white !important;
        border-radius: 10px !important;
    }
    .stat-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        border: 1px solid #3b82f6;
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
        color: #60a5fa;
    }
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #1a1a2e; }
    ::-webkit-scrollbar-thumb { background: #3b82f6; border-radius: 10px; }
</style>
"""

app.index_string = f'''
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
        {custom_css}
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
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


# ── LOGIN PAGE ────────────────────────────────────────────────────────────────
login_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-shield-alt",
                               style={"fontSize": "60px", "color": "#3b82f6",
                                      "display": "block", "textAlign": "center",
                                      "marginBottom": "15px"}),
                        html.H3("Security Log Prioritization System",
                                className="text-center mb-2",
                                style={"color": "#60a5fa", "fontWeight": "bold"}),
                        html.P("CBU — DICT Security Dashboard",
                               className="text-center mb-4",
                               style={"color": "#94a3b8"}),
                    ]),

                    dbc.Tabs([
                        # ── LOGIN TAB
                        dbc.Tab(label="🔐 Login", tab_id="login-tab", children=[
                            html.Br(),
                            html.Div(id="login-error", className="mb-3"),
                            dbc.Label("Username", className="text-white mb-1"),
                            dbc.Input(
                                id="login-username", type="text",
                                placeholder="Enter your username",
                                className="custom-input mb-3"
                            ),
                            dbc.Label("Password", className="text-white mb-1"),
                            dbc.Input(
                                id="login-password", type="password",
                                placeholder="Enter your password",
                                className="custom-input mb-4"
                            ),
                            dbc.Button(
                                [html.I(className="fas fa-sign-in-alt me-2"),
                                 "Login to Dashboard"],
                                id="login-btn", color="primary",
                                className="w-100", n_clicks=0,
                                style={"background": "linear-gradient(135deg, #3b82f6, #2563eb)",
                                       "border": "none", "borderRadius": "10px",
                                       "fontWeight": "bold", "padding": "12px"}
                            ),
                        ]),

                        # ── REGISTER TAB
                        dbc.Tab(label="📝 Sign Up", tab_id="register-tab", children=[
                            html.Br(),
                            html.Div(id="register-message", className="mb-3"),
                            dbc.Label("Username", className="text-white mb-1"),
                            dbc.Input(
                                id="reg-username", type="text",
                                placeholder="Choose a username",
                                className="custom-input mb-3"
                            ),
                            dbc.Label("Email", className="text-white mb-1"),
                            dbc.Input(
                                id="reg-email", type="email",
                                placeholder="Enter your email",
                                className="custom-input mb-3"
                            ),
                            dbc.Label("Password", className="text-white mb-1"),
                            dbc.Input(
                                id="reg-password", type="password",
                                placeholder="Min 6 characters",
                                className="custom-input mb-3"
                            ),
                            dbc.Label("Confirm Password", className="text-white mb-1"),
                            dbc.Input(
                                id="reg-confirm-password", type="password",
                                placeholder="Confirm your password",
                                className="custom-input mb-3"
                            ),
                            dbc.Label("Role", className="text-white mb-1"),
                            dcc.Dropdown(
                                id="reg-role",
                                options=[
                                    {"label": "Security Analyst", "value": "security_analyst"},
                                    {"label": "Admin", "value": "admin"},
                                    {"label": "Viewer", "value": "viewer"},
                                ],
                                value="security_analyst",
                                clearable=False,
                                style={"backgroundColor": "#0f172a", "color": "white",
                                       "border": "2px solid #3b82f6",
                                       "borderRadius": "10px", "marginBottom": "20px"}
                            ),
                            dbc.Button(
                                [html.I(className="fas fa-user-plus me-2"),
                                 "Create Account"],
                                id="register-btn", color="success",
                                className="w-100", n_clicks=0,
                                style={"background": "linear-gradient(135deg, #10b981, #059669)",
                                       "border": "none", "borderRadius": "10px",
                                       "fontWeight": "bold", "padding": "12px"}
                            ),
                        ]),
                    ], active_tab="login-tab"),

                    html.Hr(style={"borderColor": "#3b82f6", "marginTop": "20px"}),
                    html.P("Powered by Machine Learning | CBU DICT Security Operations",
                           className="text-center mt-2",
                           style={"color": "#64748b", "fontSize": "11px"})
                ])
            ], className="login-card")
        ], width=5, lg=4, md=6)
    ], justify="center", style={"marginTop": "8vh", "padding": "20px"})
], fluid=True, style={"minHeight": "100vh"})


# ── DASHBOARD PAGE ────────────────────────────────────────────────────────────
def dashboard_layout(username, role):
    return dbc.Container([

        # ── Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-chart-line",
                           style={"fontSize": "28px", "color": "#3b82f6",
                                  "marginRight": "12px"}),
                    html.H4("ML-Driven Windows Security Log Prioritization",
                            className="mb-0",
                            style={"color": "#f8fafc", "fontWeight": "bold"}),
                ], style={"display": "flex", "alignItems": "center"})
            ], width=8),
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-user-circle",
                           style={"fontSize": "18px", "color": "#3b82f6"}),
                    html.Span(f"  {username}",
                              style={"color": "#e2e8f0", "marginLeft": "6px"}),
                    html.Span(f"  [{role}]",
                              style={"color": "#3b82f6", "fontSize": "12px",
                                     "marginLeft": "4px"}),
                    dbc.Button(
                        [html.I(className="fas fa-sign-out-alt"), " Logout"],
                        id="logout-btn", color="danger", size="sm",
                        style={"marginLeft": "15px",
                               "background": "linear-gradient(135deg, #ef4444, #dc2626)",
                               "border": "none", "borderRadius": "8px"}
                    )
                ], style={"display": "flex", "alignItems": "center",
                           "justifyContent": "flex-end"})
            ], width=4),
        ], className="mb-4",
           style={"padding": "20px 0", "borderBottom": "2px solid #3b82f6"}),

        # ── Summary Cards
        dbc.Row([
            dbc.Col(html.Div([
                html.I(className="fas fa-fire",
                       style={"fontSize": "28px", "color": "#ef4444",
                              "marginBottom": "8px"}),
                html.H5("High Priority", style={"color": "#ef4444"}),
                html.H2(id="high-count", className="stat-number",
                        style={"color": "#ef4444"})
            ], className="stat-card"), width=3),

            dbc.Col(html.Div([
                html.I(className="fas fa-exclamation-triangle",
                       style={"fontSize": "28px", "color": "#f59e0b",
                              "marginBottom": "8px"}),
                html.H5("Medium Priority", style={"color": "#f59e0b"}),
                html.H2(id="medium-count", className="stat-number",
                        style={"color": "#f59e0b"})
            ], className="stat-card"), width=3),

            dbc.Col(html.Div([
                html.I(className="fas fa-check-circle",
                       style={"fontSize": "28px", "color": "#10b981",
                              "marginBottom": "8px"}),
                html.H5("Low Priority", style={"color": "#10b981"}),
                html.H2(id="low-count", className="stat-number",
                        style={"color": "#10b981"})
            ], className="stat-card"), width=3),

            dbc.Col(html.Div([
                html.I(className="fas fa-database",
                       style={"fontSize": "28px", "color": "#3b82f6",
                              "marginBottom": "8px"}),
                html.H5("Total Events", style={"color": "#3b82f6"}),
                html.H2(id="total-count", className="stat-number")
            ], className="stat-card"), width=3),
        ], className="mb-4"),

        # ── Charts
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Priority Distribution",
                                       style={"color": "#3b82f6"})),
                dbc.CardBody(dcc.Graph(id="priority-pie"))
            ], className="custom-card"), width=4),

            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Risk Score Distribution",
                                       style={"color": "#3b82f6"})),
                dbc.CardBody(dcc.Graph(id="risk-histogram"))
            ], className="custom-card"), width=4),

            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Feature Importance",
                                       style={"color": "#3b82f6"})),
                dbc.CardBody(dcc.Graph(id="feature-importance-chart"))
            ], className="custom-card"), width=4),
        ], className="mb-4"),

        # ── Filters + Manual Refresh (NO AUTO-REFRESH)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("🔍 Filters & Data Refresh", style={"color": "#3b82f6"})),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label("Priority Level",
                                           style={"color": "#e2e8f0"}),
                                dcc.Dropdown(
                                    id="priority-filter",
                                    options=[
                                        {"label": "All Events",      "value": "All"},
                                        {"label": "🔴 High Priority", "value": "High"},
                                        {"label": "🟡 Medium Priority","value": "Medium"},
                                        {"label": "🟢 Low Priority",  "value": "Low"},
                                    ],
                                    value="All", clearable=False,
                                    style={"backgroundColor": "#0f172a",
                                           "border": "1px solid #3b82f6"}
                                )
                            ], width=4),

                            dbc.Col([
                                html.Label("Hour Range (0–23)",
                                           style={"color": "#e2e8f0"}),
                                dcc.RangeSlider(
                                    id="hour-filter",
                                    min=0, max=23, step=1,
                                    value=[0, 23],
                                    marks={i: str(i) for i in range(0, 24, 4)},
                                    tooltip={"placement": "bottom",
                                             "always_visible": True}
                                )
                            ], width=5),

                            dbc.Col([
                                html.Label(" ", style={"color": "#0f172a"}),
                                html.Br(),
                                dbc.Button(
                                    [html.I(className="fas fa-sync-alt me-2"),
                                     "Refresh Data"],
                                    id="refresh-btn", color="primary",
                                    className="w-100", n_clicks=0,
                                    style={"background":
                                               "linear-gradient(135deg, #3b82f6, #2563eb)",
                                           "border": "none",
                                           "borderRadius": "10px",
                                           "fontWeight": "bold"}
                                )
                            ], width=3),
                        ]),
                        html.Div(id="last-updated", className="mt-2 text-muted", style={"color": "#94a3b8"})
                    ])
                ], className="custom-card")
            ])
        ], className="mb-4"),

        # ── Events Table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(
                        html.H5("📋 Prioritized Security Events",
                                style={"color": "#3b82f6"})
                    ),
                    dbc.CardBody([
                        dash_table.DataTable(
                            id="events-table",
                            page_size=15,
                            style_table={"overflowX": "auto",
                                         "backgroundColor": "#0f172a"},
                            style_header={
                                "backgroundColor": "#1e293b",
                                "color"          : "#3b82f6",
                                "fontWeight"     : "bold",
                                "border"         : "1px solid #334155"
                            },
                            style_data={
                                "backgroundColor": "#0f172a",
                                "color"          : "#e2e8f0",
                                "border"         : "1px solid #334155"
                            },
                            style_data_conditional=[
                                {"if": {"filter_query": '{priority} = "High"'},
                                 "backgroundColor": "#450a0a",
                                 "color": "#fca5a5"},
                                {"if": {"filter_query": '{priority} = "Medium"'},
                                 "backgroundColor": "#451a03",
                                 "color": "#fcd34d"},
                                {"if": {"filter_query": '{priority} = "Low"'},
                                 "backgroundColor": "#022c22",
                                 "color": "#6ee7b7"},
                            ],
                            sort_action  ="native",
                            filter_action="native",
                            page_current =0,
                        )
                    ])
                ], className="custom-card")
            ])
        ], className="mb-4"),

        # ── SHAP Explanation
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(
                        html.H5("🧠 SHAP Feature Explanation",
                                style={"color": "#3b82f6"})
                    ),
                    dbc.CardBody([
                        html.P(
                            "Enter an event index number to understand WHY "
                            "it was given its priority level.",
                            style={"color": "#94a3b8"}
                        ),
                        dbc.Row([
                            dbc.Col([
                                dbc.InputGroup([
                                    dbc.InputGroupText(
                                        html.I(className="fas fa-hashtag"),
                                        style={"backgroundColor": "#3b82f6",
                                               "border": "none", "color": "white"}
                                    ),
                                    dbc.Input(
                                        id="shap-index", type="number",
                                        value=0, min=0,
                                        placeholder="Event index (e.g. 0, 1, 2...)",
                                        className="custom-input"
                                    )
                                ])
                            ], width=4),
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="fas fa-chart-bar me-2"),
                                     "Explain This Event"],
                                    id="shap-btn", color="info", n_clicks=0,
                                    style={"background":
                                               "linear-gradient(135deg, #06b6d4, #0891b2)",
                                           "border": "none",
                                           "borderRadius": "10px",
                                           "fontWeight": "bold",
                                           "width": "100%"}
                                )
                            ], width=3),
                        ], className="mb-3"),
                        html.Div(id="shap-interpretation", className="mb-2"),
                        dcc.Graph(id="shap-chart")
                    ])
                ], className="custom-card")
            ])
        ]),

        # NO AUTO-REFRESH - removed dcc.Interval

    ], fluid=True, style={"padding": "20px", "minHeight": "100vh"})


# ── MAIN LAYOUT ───────────────────────────────────────────────────────────────
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="auth-store", storage_type="session"),
    html.Div(id="page-content")
])


# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_headers(auth_data):
    if auth_data and isinstance(auth_data, dict) and auth_data.get("token"):
        return {"Authorization": f"Bearer {auth_data['token']}"}
    return {}

def empty_fig():
    return go.Figure().update_layout(
        paper_bgcolor="#0f172a",
        plot_bgcolor ="#0f172a",
        font_color   ="white"
    )


# ── CALLBACKS ─────────────────────────────────────────────────────────────────

@app.callback(
    Output("page-content", "children"),
    Input("url",        "pathname"),
    Input("auth-store", "data"),
)
def display_page(pathname, auth_data):
    if auth_data and isinstance(auth_data, dict) and auth_data.get("token"):
        return dashboard_layout(auth_data["username"], auth_data["role"])
    return login_layout


@app.callback(
    Output("auth-store",  "data",     allow_duplicate=True),
    Output("login-error", "children"),
    Input("login-btn",    "n_clicks"),
    State("login-username", "value"),
    State("login-password", "value"),
    prevent_initial_call=True
)
def handle_login(n_clicks, username, password):
    if not username or not password:
        return None, dbc.Alert("Please enter username and password", color="danger")
    try:
        response = requests.post(
            f"{API}/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "token"   : data["access_token"],
                "username": data["username"],
                "role"    : data["role"]
            }, ""
        elif response.status_code == 401:
            return None, dbc.Alert("Invalid username or password", color="danger")
        elif response.status_code == 403:
            return None, dbc.Alert("Account is disabled", color="danger")
        else:
            return None, dbc.Alert(f"Login failed: {response.text}", color="danger")
    except Exception as e:
        return None, dbc.Alert(f"Cannot reach server: {str(e)}", color="danger")


@app.callback(
    Output("register-message", "children"),
    Input("register-btn",      "n_clicks"),
    State("reg-username",         "value"),
    State("reg-email",            "value"),
    State("reg-password",         "value"),
    State("reg-confirm-password", "value"),
    State("reg-role",             "value"),
    prevent_initial_call=True
)
def handle_register(n_clicks, username, email, password, confirm_password, role):
    if not all([username, email, password, confirm_password]):
        return dbc.Alert("Please fill in all fields", color="danger")
    if password != confirm_password:
        return dbc.Alert("Passwords do not match", color="danger")
    if len(password) < 6:
        return dbc.Alert("Password must be at least 6 characters", color="danger")
    if len(password.encode("utf-8")) > 72:
        return dbc.Alert("Password too long — maximum 72 characters", color="danger")
    try:
        response = requests.post(
            f"{API}/register",
            json={"username": username, "email": email,
                  "password": password, "role": role},
            timeout=10
        )
        if response.status_code == 200:
            return dbc.Alert(
                [html.B("✅ Account created! "),
                 "Switch to the Login tab to sign in."],
                color="success"
            )
        detail = response.json().get("detail", "Unknown error")
        if "username" in detail.lower():
            return dbc.Alert("Username already exists", color="danger")
        elif "email" in detail.lower():
            return dbc.Alert("Email already registered", color="danger")
        return dbc.Alert(f"Registration failed: {detail}", color="danger")
    except Exception as e:
        return dbc.Alert(f"Cannot reach server: {str(e)}", color="danger")


@app.callback(
    Output("auth-store", "data",        allow_duplicate=True),
    Output("url",        "pathname",    allow_duplicate=True),
    Input("logout-btn",  "n_clicks"),
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    return None, "/"


# Main callback for summary - ONLY on refresh button click (NO auto-refresh)
@app.callback(
    Output("high-count",     "children"),
    Output("medium-count",   "children"),
    Output("low-count",      "children"),
    Output("total-count",    "children"),
    Output("priority-pie",   "figure"),
    Output("risk-histogram", "figure"),
    Output("last-updated",   "children"),
    Input("refresh-btn",     "n_clicks"),
    State("auth-store",      "data"),
)
def update_summary(btn_clicks, auth_data):
    from datetime import datetime
    
    print(f"Refresh button clicked: {btn_clicks}")
    
    if not auth_data or not isinstance(auth_data, dict) or not auth_data.get("token"):
        return "—", "—", "—", "—", empty_fig(), empty_fig(), "Please login to view data"

    try:
        headers = get_headers(auth_data)

        summary_resp = requests.get(
            f"{API}/priority-summary", headers=headers, timeout=30
        )
        events_resp  = requests.get(
            f"{API}/prioritized", headers=headers, timeout=30
        )

        if summary_resp.status_code != 200 or events_resp.status_code != 200:
            print(f"API errors - Summary: {summary_resp.status_code}, Events: {events_resp.status_code}")
            return "—", "—", "—", "—", empty_fig(), empty_fig(), f"API Error: {summary_resp.status_code}"

        summary = summary_resp.json()
        events  = events_resp.json()
        
        print(f"Summary data: {summary}")
        print(f"Events count: {len(events) if isinstance(events, list) else 0}")

        high   = summary.get("High",   0)
        medium = summary.get("Medium", 0)
        low    = summary.get("Low",    0)
        total  = summary.get("Total",  0)

        pie = px.pie(
            names  = ["High", "Medium", "Low"],
            values = [high, medium, low],
            color  = ["High", "Medium", "Low"],
            color_discrete_map={
                "High"  : "#ef4444",
                "Medium": "#f59e0b",
                "Low"   : "#10b981"
            }
        )
        pie.update_layout(
            paper_bgcolor="#0f172a",
            font_color   ="white"
        )

        df = pd.DataFrame(events)
        if not df.empty and "risk_score" in df.columns:
            hist = px.histogram(
                df, x="risk_score", nbins=50,
                color_discrete_sequence=["#3b82f6"]
            )
            hist.update_layout(
                paper_bgcolor="#0f172a",
                plot_bgcolor ="#0f172a",
                font_color   ="white"
            )
        else:
            hist = empty_fig()

        last_updated = f"✅ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return str(high), str(medium), str(low), str(total), pie, hist, last_updated

    except Exception as e:
        print(f"update_summary error: {e}")
        import traceback
        traceback.print_exc()
        return "—", "—", "—", "—", empty_fig(), empty_fig(), f"Error: {str(e)}"


# Callback for table and feature importance - ONLY on refresh button and filters
@app.callback(
    Output("events-table",             "data"),
    Output("events-table",             "columns"),
    Output("feature-importance-chart", "figure"),
    Input("refresh-btn",               "n_clicks"),
    Input("priority-filter",           "value"),
    Input("hour-filter",               "value"),
    State("auth-store",                "data"),
)
def update_table(btn_clicks, priority_filter, hour_range, auth_data):
    print(f"Updating table - refresh clicks: {btn_clicks}, priority: {priority_filter}")
    
    if not auth_data or not isinstance(auth_data, dict) or not auth_data.get("token"):
        return [], [], empty_fig()

    try:
        headers = get_headers(auth_data)

        events_resp = requests.get(
            f"{API}/prioritized", headers=headers, timeout=30
        )
        imp_resp    = requests.get(
            f"{API}/feature-importance", headers=headers, timeout=10
        )

        if events_resp.status_code != 200:
            print(f"Events API error: {events_resp.status_code}")
            return [], [], empty_fig()

        df = pd.DataFrame(events_resp.json())
        if df.empty:
            print("No events data received")
            return [], [], empty_fig()

        # Apply filters
        if priority_filter and priority_filter != "All" and "priority" in df.columns:
            df = df[df["priority"] == priority_filter]

        if "hour" in df.columns and hour_range:
            df = df[
                (df["hour"] >= hour_range[0]) &
                (df["hour"] <= hour_range[1])
            ]

        if "risk_score" in df.columns:
            df["risk_score"] = df["risk_score"].round(4)

        display_cols = ["event_id", "hour", "day_of_week", "risk_score", "priority"]
        display_cols = [c for c in display_cols if c in df.columns]
        columns      = [{"name": c.replace("_", " ").title(), "id": c}
                        for c in display_cols]
        data         = df[display_cols].to_dict(orient="records")
        
        print(f"Table data rows: {len(data)}")

        # Feature importance chart
        if imp_resp.status_code == 200:
            imp    = imp_resp.json()
            imp_df = pd.DataFrame(
                list(imp.items()), columns=["Feature", "Importance"]
            ).sort_values("Importance", ascending=True)
            bar = px.bar(
                imp_df, x="Importance", y="Feature",
                orientation="h", color="Importance",
                color_continuous_scale="Blues"
            )
            bar.update_layout(
                paper_bgcolor="#0f172a",
                plot_bgcolor ="#0f172a",
                font_color   ="white",
                height       =400
            )
        else:
            print(f"Feature importance API error: {imp_resp.status_code}")
            bar = empty_fig()

        return data, columns, bar

    except Exception as e:
        print(f"update_table error: {e}")
        import traceback
        traceback.print_exc()
        return [], [], empty_fig()


@app.callback(
    Output("shap-chart",          "figure"),
    Output("shap-interpretation", "children"),
    Input("shap-btn",             "n_clicks"),
    State("shap-index",           "value"),
    State("auth-store",           "data"),
    prevent_initial_call=True
)
def update_shap(n_clicks, event_index, auth_data):
    print(f"SHAP called for event index: {event_index}")

    if not auth_data or not isinstance(auth_data, dict):
        return empty_fig(), dbc.Alert(
            "Session data missing — please refresh the page", color="warning"
        )

    token = auth_data.get("token")
    if not token:
        return empty_fig(), dbc.Alert(
            "Token missing — please log out and log in again", color="warning"
        )

    if event_index is None:
        event_index = 0

    try:
        headers   = {"Authorization": f"Bearer {token}"}
        resp      = requests.get(
            f"{API}/shap/{event_index}",
            headers=headers,
            timeout=60
        )

        if resp.status_code == 401:
            return empty_fig(), dbc.Alert(
                "Session expired — please log out and log in again",
                color="danger"
            )
        if resp.status_code != 200:
            return empty_fig(), dbc.Alert(
                f"API error {resp.status_code}: {resp.text}", color="danger"
            )

        shap_data = resp.json()

        if "error" in shap_data:
            return empty_fig(), dbc.Alert(shap_data["error"], color="danger")

        features     = shap_data.get("feature_names", [])
        shap_vals    = shap_data.get("shap_values",   [])
        feature_vals = shap_data.get("feature_values", [])

        if not features or not shap_vals:
            return empty_fig(), dbc.Alert(
                "No SHAP data returned for this event", color="warning"
            )

        sorted_pairs = sorted(
            zip(features, shap_vals, feature_vals),
            key=lambda x: abs(x[1]), reverse=True
        )[:15]
        features_s, shap_s, vals_s = zip(*sorted_pairs)

        fig = go.Figure(go.Bar(
            x           = list(shap_s),
            y           = [f"{f} = {round(v, 2)}"
                           for f, v in zip(features_s, vals_s)],
            orientation = "h",
            marker_color= ["#ef4444" if v > 0 else "#10b981"
                           for v in shap_s],
            text        = [f"{v:.3f}" for v in shap_s],
            textposition= "outside"
        ))
        fig.update_layout(
            title        = f"SHAP Explanation — Event {event_index}",
            xaxis_title  = "SHAP Value (Red = increases risk | Green = reduces risk)",
            paper_bgcolor= "#0f172a",
            plot_bgcolor = "#0f172a",
            font_color   = "white",
            height       = 500,
            margin       = dict(l=220, r=60, t=60, b=60)
        )

        top_f = features_s[0]
        top_v = shap_s[0]
        direction = "increased" if top_v > 0 else "reduced"

        interpretation = dbc.Alert([
            html.B("📖 How to read this chart:"), html.Br(),
            html.Span("🔴 Red bars ", style={"color": "#ef4444", "fontWeight": "bold"}),
            "= features that INCREASED the risk score", html.Br(),
            html.Span("🟢 Green bars ", style={"color": "#10b981", "fontWeight": "bold"}),
            "= features that REDUCED the risk score", html.Br(),
            "The longer the bar, the stronger its influence.", html.Br(), html.Br(),
            html.B("📌 Top influencing feature: "),
            html.Span(top_f, style={"color": "#60a5fa"}),
            f" — this {direction} the risk for event {event_index}."
        ], color="info")

        return fig, interpretation

    except Exception as e:
        print(f"SHAP error: {e}")
        import traceback
        traceback.print_exc()
        return empty_fig(), dbc.Alert(f"Error: {str(e)}", color="danger")


# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Security Log Prioritization Dashboard")
    print("=" * 60)
    print(f"📡 Backend API : {API}")
    print(f"🌐 Dashboard   : http://127.0.0.1:8050")
    print("=" * 60)
    print("⚠️  Make sure FastAPI is running on port 8000 first")
    print("📊 Data only updates when you click 'Refresh Data' button")
    print("=" * 60 + "\n")

    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8050")

    threading.Timer(1.5, open_browser).start()
    app.run(debug=True, port=8050, host="127.0.0.1")