from dash import dcc, html, dash_table, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import requests
import pandas as pd

API = "http://127.0.0.1:8000"

CLASS_LABELS = {
    0: "Auditing settings on object were changed.",
    1: "Logon",
    2: "Other",
    3: "Special Logon",
    4: "User Account Management",
}


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


# ── DASHBOARD LAYOUT ──────────────────────────────────────────────────────────
def dashboard_layout(username, role):
    is_admin = role in ["system_admin", "admin"]

    return dbc.Container([

        # ── Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-shield-alt",
                           style={"fontSize": "26px", "color": "#3b82f6",
                                  "marginRight": "12px"}),
                    html.H3("Security Log Prioritization",
                            className="mb-0",
                            style={"color": "#f8fafc", "fontWeight": "600",
                                   "letterSpacing": "-0.5px"}),
                    html.Small("ML‑Driven Analytics • CBU DICT",
                               style={"color": "#94a3b8", "marginLeft": "12px",
                                      "fontSize": "12px"}),
                ], style={"display": "flex", "alignItems": "center"})
            ], width=8),
            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-user-circle",
                               style={"fontSize": "18px", "color": "#3b82f6"}),
                        html.Span(f" {username}  •  ",
                                  style={"color": "#cbd5e1", "marginLeft": "6px"}),
                        html.Span(f"{role}",
                                  style={"color": "#3b82f6", "fontWeight": "500"}),
                    ], className="me-3"),
                    dbc.Button(
                        [html.I(className="fas fa-sign-out-alt me-2"), "Logout"],
                        id="logout-btn", color="danger", size="sm", outline=True,
                        style={"borderRadius": "20px", "padding": "4px 16px"}
                    )
                ], style={"display": "flex", "alignItems": "center",
                           "justifyContent": "flex-end"})
            ], width=4),
        ], className="mb-4 pb-2",
           style={"borderBottom": "1px solid #2d3748"}),

        # ── ADMIN PANEL — only visible to admins
        dbc.Row([dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-cogs me-2",
                           style={"color": "#6366f1"}),
                    html.Span("Admin Controls — Model Management",
                              style={"color": "#6366f1", "fontWeight": "600"})
                ]),
                dbc.CardBody([
                    html.Div(id="active-model-display", className="mb-3"),
                    html.Div(id="switch-model-message", className="mb-3"),
                    html.P(
                        "Switch the active classification model. "
                        "Rebuilding cache may take a minute.",
                        style={"color": "#94a3b8", "fontSize": "12px",
                               "marginBottom": "16px"}
                    ),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                [html.I(className="fas fa-bolt me-2"),
                                 "Switch to XGBoost"],
                                id="switch-xgboost-btn", n_clicks=0,
                                className="w-100",
                                style={"background":
                                           "linear-gradient(135deg, #f59e0b, #d97706)",
                                       "border"      : "none",
                                       "borderRadius": "8px",
                                       "fontWeight"  : "500",
                                       "color"       : "white"}
                            )
                        ], width=4),
                        dbc.Col([
                            dbc.Button(
                                [html.I(className="fas fa-tree me-2"),
                                 "Switch to Random Forest"],
                                id="switch-rf-btn", n_clicks=0,
                                className="w-100",
                                style={"background":
                                           "linear-gradient(135deg, #10b981, #059669)",
                                       "border"      : "none",
                                       "borderRadius": "8px",
                                       "fontWeight"  : "500",
                                       "color"       : "white"}
                            )
                        ], width=4),
                        dbc.Col([
                            dbc.Button(
                                [html.I(className="fas fa-sync-alt me-2"),
                                 "Rebuild Cache"],
                                id="rebuild-cache-btn", n_clicks=0,
                                className="w-100",
                                style={"background":
                                           "linear-gradient(135deg, #6366f1, #4f46e5)",
                                       "border"      : "none",
                                       "borderRadius": "8px",
                                       "fontWeight"  : "500",
                                       "color"       : "white"}
                            )
                        ], width=4),
                    ])
                ])
            ], className="shadow-sm mb-4",
               style={"backgroundColor": "#1e293b",
                      "border"         : "1px solid #6366f1"})
        ])])
        if is_admin else html.Div(
            # Hidden placeholder buttons so callbacks don't break for analysts
            [
                html.Div(id="active-model-display",    style={"display": "none"}),
                html.Div(id="switch-model-message",    style={"display": "none"}),
                html.Button(id="switch-xgboost-btn",   style={"display": "none"},
                            n_clicks=0),
                html.Button(id="switch-rf-btn",        style={"display": "none"},
                            n_clicks=0),
                html.Button(id="rebuild-cache-btn",    style={"display": "none"},
                            n_clicks=0),
            ]
        ),

        # ── Stats Cards
        dbc.Row([
            dbc.Col(_stat_card("🔥", "#ef4444", "High Priority",   "high-count"),   width=3),
            dbc.Col(_stat_card("⚠️", "#f59e0b", "Medium Priority", "medium-count"), width=3),
            dbc.Col(_stat_card("✅", "#10b981", "Low Priority",    "low-count"),    width=3),
            dbc.Col(_stat_card("📊", "#3b82f6", "Total Events",    "total-count"),  width=3),
        ], className="mb-4 g-3"),

        # ── Charts
        dbc.Row([
            dbc.Col(_chart_card("Priority Distribution",  "priority-pie"),            width=4),
            dbc.Col(_chart_card("Risk Score Distribution","risk-histogram"),           width=4),
            dbc.Col(_chart_card("Feature Importance",     "feature-importance-chart"), width=4),
        ], className="mb-4 g-3"),

        # ── Filters + Events Table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("🔍 Filters", className="mb-0",
                                           style={"color": "#3b82f6"})),
                    dbc.CardBody([
                        dbc.Label("Priority Level", className="mb-1",
                                  style={"color": "#cbd5e1", "fontSize": "12px"}),
                        dbc.Select(
                            id="priority-filter",
                            options=[
                                {"label": "All Events",       "value": "All"},
                                {"label": "🔴 High",           "value": "High"},
                                {"label": "🟡 Medium",         "value": "Medium"},
                                {"label": "🟢 Low",            "value": "Low"},
                            ],
                            value="All", className="mb-3",
                            style={"backgroundColor": "#0f172a",
                                   "border": "1px solid #3b82f6", "color": "white"}
                        ),
                        dbc.Label("Hour Range (0–23)", className="mb-1",
                                  style={"color": "#cbd5e1", "fontSize": "12px"}),
                        dcc.RangeSlider(
                            id="hour-filter", min=0, max=23, step=1,
                            value=[0, 23],
                            marks={0: "0", 6: "6", 12: "12", 18: "18", 23: "23"},
                            tooltip={"placement": "bottom", "always_visible": False}
                        ),
                        html.Hr(className="my-3",
                                style={"borderColor": "#2d3748"}),
                        dbc.Button(
                            [html.I(className="fas fa-sync-alt me-2"),
                             "Refresh Data"],
                            id="refresh-btn", color="primary", className="w-100",
                            style={"borderRadius": "8px", "fontWeight": "500"}
                        ),
                    ])
                ], className="h-100 shadow-sm",
                   style={"backgroundColor": "#1e293b", "border": "none"})
            ], width=4),

            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(
                        html.H5("📋 Prioritized Security Events",
                                className="mb-0",
                                style={"color": "#3b82f6"})
                    ),
                    dbc.CardBody([
                        dash_table.DataTable(
                            id="events-table",
                            page_size=12,
                            style_table={"overflowX": "auto",
                                         "minHeight": "380px"},
                            style_header={
                                "backgroundColor": "#0f172a",
                                "color"          : "#3b82f6",
                                "fontWeight"     : "600",
                                "fontSize"       : "12px",
                                "border"         : "none",
                                "padding"        : "8px"
                            },
                            style_data={
                                "backgroundColor": "#1e293b",
                                "color"          : "#e2e8f0",
                                "fontSize"       : "12px",
                                "border"         : "none",
                                "padding"        : "6px"
                            },
                            style_data_conditional=[
                                {"if": {"filter_query": '{priority} = "High"'},
                                 "backgroundColor": "#7f1a1a",
                                 "color"          : "#fca5a5"},
                                {"if": {"filter_query": '{priority} = "Medium"'},
                                 "backgroundColor": "#78350f",
                                 "color"          : "#fcd34d"},
                                {"if": {"filter_query": '{priority} = "Low"'},
                                 "backgroundColor": "#064e3b",
                                 "color"          : "#6ee7b7"},
                            ],
                            sort_action  ="native",
                            filter_action="native",
                            page_current =0,
                        )
                    ])
                ], className="h-100 shadow-sm",
                   style={"backgroundColor": "#1e293b", "border": "none"})
            ], width=8),
        ], className="mb-4 g-3"),

        # ── SHAP + Feedback
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(
                        html.H5("🧠 SHAP Feature Explanation",
                                className="mb-0",
                                style={"color": "#3b82f6"})
                    ),
                    dbc.CardBody([
                        html.P("Explain why a specific event was classified this way.",
                               style={"color": "#94a3b8", "fontSize": "12px",
                                      "marginBottom": "12px"}),
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
                                        placeholder="Event index",
                                        style={"backgroundColor": "#0f172a",
                                               "border"         : "1px solid #3b82f6",
                                               "color"          : "white"}
                                    )
                                ])
                            ], width=7),
                            dbc.Col([
                                dbc.Button(
                                    "Explain", id="shap-btn",
                                    color="info", className="w-100",
                                    style={"backgroundColor": "#0891b2",
                                           "border"         : "none",
                                           "fontWeight"     : "500"}
                                )
                            ], width=5),
                        ], className="mb-3"),
                        html.Div(id="shap-interpretation", className="mb-2"),
                        dcc.Graph(id="shap-chart",
                                  config={"displayModeBar": False})
                    ])
                ], className="h-100 shadow-sm",
                   style={"backgroundColor": "#1e293b", "border": "none"})
            ], width=6),

            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(
                        html.H5("📝 Analyst Feedback", className="mb-0",
                                style={"color": "#3b82f6"})
                    ),
                    dbc.CardBody([
                        html.P("Help improve the model by providing feedback.",
                               style={"color": "#94a3b8", "fontSize": "12px",
                                      "marginBottom": "12px"}),
                        html.Div(id="feedback-message", className="mb-2"),
                        dbc.Label("Correct Label", className="mb-1",
                                  style={"color": "#cbd5e1", "fontSize": "12px"}),
                        dbc.Select(
                            id="feedback-correct-label",
                            options=[{"label": v, "value": v}
                                     for v in CLASS_LABELS.values()],
                            placeholder="Select correct classification...",
                            style={"backgroundColor": "#0f172a",
                                   "border"         : "1px solid #f59e0b",
                                   "color"          : "white",
                                   "marginBottom"   : "12px"}
                        ),
                        dbc.Label("Was it correctly classified?",
                                  className="mb-1",
                                  style={"color": "#cbd5e1", "fontSize": "12px"}),
                        dbc.Select(
                            id="feedback-correct-flag",
                            options=[
                                {"label": "✅ Yes", "value": "true"},
                                {"label": "❌ No",  "value": "false"},
                            ],
                            value="true",
                            style={"backgroundColor": "#0f172a",
                                   "border"         : "1px solid #f59e0b",
                                   "color"          : "white",
                                   "marginBottom"   : "12px"}
                        ),
                        dbc.Label("Analyst Comment", className="mb-1",
                                  style={"color": "#cbd5e1", "fontSize": "12px"}),
                        dbc.Textarea(
                            id="feedback-comment",
                            placeholder="Additional context...",
                            rows=2,
                            style={"backgroundColor": "#0f172a",
                                   "border"         : "1px solid #3b82f6",
                                   "color"          : "white",
                                   "borderRadius"   : "8px",
                                   "marginBottom"   : "16px"}
                        ),
                        dbc.Button(
                            [html.I(className="fas fa-paper-plane me-2"),
                             "Submit Feedback"],
                            id="feedback-btn", color="warning",
                            className="w-100",
                            style={"backgroundColor": "#d97706",
                                   "border"         : "none",
                                   "fontWeight"     : "500"}
                        ),
                    ])
                ], className="h-100 shadow-sm",
                   style={"backgroundColor": "#1e293b", "border": "none"})
            ], width=6),
        ], className="mb-4 g-3"),

        # ── Feedback History
        dbc.Row([dbc.Col([
            dbc.Card([
                dbc.CardHeader(
                    html.H5("📊 Feedback History", className="mb-0",
                            style={"color": "#3b82f6"})
                ),
                dbc.CardBody([
                    html.Div(id="feedback-table-container")
                ])
            ], className="shadow-sm",
               style={"backgroundColor": "#1e293b", "border": "none"})
        ])], className="g-3"),

    ], fluid=True,
       style={"padding": "24px", "backgroundColor": "#0f172a",
              "minHeight": "100vh"})


# ── LAYOUT HELPERS ────────────────────────────────────────────────────────────
def _stat_card(icon, color, label, count_id):
    return html.Div([
        html.Div(icon, style={"fontSize": "32px", "color": color,
                               "marginBottom": "8px"}),
        html.H6(label, style={"color": "#cbd5e1", "fontSize": "12px",
                               "margin": "0", "textTransform": "uppercase",
                               "letterSpacing": "0.5px"}),
        html.H2(id=count_id, style={"fontSize": "2rem", "fontWeight": "700",
                                     "color": color, "margin": "0",
                                     "lineHeight": "1.2"})
    ], className="text-center p-3 rounded-3 shadow-sm",
       style={"backgroundColor": "#1e293b",
              "borderLeft"     : f"4px solid {color}"})

def _chart_card(title, graph_id):
    return dbc.Card([
        dbc.CardHeader(
            html.H6(title, className="mb-0",
                    style={"color": "#3b82f6", "fontWeight": "600"})
        ),
        dbc.CardBody(dcc.Graph(id=graph_id,
                               config={"displayModeBar": False}))
    ], className="shadow-sm",
       style={"backgroundColor": "#1e293b", "border": "none", "height": "100%"})


# ── CALLBACKS ─────────────────────────────────────────────────────────────────
def register_dashboard_callbacks(app):

    @app.callback(
        Output("auth-store", "data",     allow_duplicate=True),
        Output("url",        "pathname", allow_duplicate=True),
        Input("logout-btn",  "n_clicks"),
        prevent_initial_call=True
    )
    def handle_logout(n_clicks):
        return None, "/"

    # ── Admin — show active model ─────────────────────────────────────────────
    @app.callback(
        Output("active-model-display", "children"),
        Input("load-trigger",          "data"),
        Input("switch-model-message",  "children"),
        State("auth-store",            "data"),
        prevent_initial_call=False
    )
    def show_active_model(_trigger, _msg, auth_data):
        if not auth_data or not auth_data.get("token"):
            return ""
        if auth_data.get("role") not in ["system_admin", "admin"]:
            return ""
        try:
            headers = get_headers(auth_data)
            resp    = requests.get(
                f"{API}/active-model", headers=headers, timeout=10
            )
            if resp.status_code == 200:
                active = resp.json().get("active_model", "xgboost")
                color  = "#f59e0b" if active == "xgboost" else "#10b981"
                icon   = "fas fa-bolt" if active == "xgboost" else "fas fa-tree"
                return dbc.Alert([
                    html.I(className=f"{icon} me-2"),
                    html.B("Active Model: "),
                    html.Span(
                        active.replace("_", " ").title(),
                        style={"color": color, "fontWeight": "bold"}
                    )
                ], color="dark", style={"border": f"1px solid {color}"})
        except:
            return ""

    # ── Admin — model switching ───────────────────────────────────────────────
    @app.callback(
        Output("switch-model-message", "children"),
        Input("switch-xgboost-btn",    "n_clicks"),
        Input("switch-rf-btn",         "n_clicks"),
        Input("rebuild-cache-btn",     "n_clicks"),
        State("auth-store",            "data"),
        prevent_initial_call=True
    )
    def handle_admin_actions(xgb_clicks, rf_clicks, cache_clicks, auth_data):
        if not auth_data or not auth_data.get("token"):
            return dbc.Alert("Not authenticated", color="danger")

        if auth_data.get("role") not in ["system_admin", "admin"]:
            return dbc.Alert(
                "❌ Access denied — admin only", color="danger"
            )

        headers   = get_headers(auth_data)
        triggered = ctx.triggered_id

        try:
            if triggered == "switch-xgboost-btn":
                resp = requests.post(
                    f"{API}/switch-model/xgboost",
                    headers=headers, timeout=120
                )
            elif triggered == "switch-rf-btn":
                resp = requests.post(
                    f"{API}/switch-model/random_forest",
                    headers=headers, timeout=120
                )
            elif triggered == "rebuild-cache-btn":
                resp = requests.post(
                    f"{API}/refresh-cache",
                    headers=headers, timeout=120
                )
            else:
                return ""

            if resp.status_code == 200:
                return dbc.Alert(
                    [html.B("✅ "),
                     resp.json().get("message", "Done")],
                    color="success"
                )
            elif resp.status_code == 403:
                return dbc.Alert(
                    "❌ Access denied — admin only", color="danger"
                )
            else:
                return dbc.Alert(
                    f"❌ Failed: {resp.json().get('detail', 'Unknown')}",
                    color="danger"
                )

        except Exception as e:
            return dbc.Alert(f"Error: {str(e)[:100]}", color="danger")

    # ── Summary cards + charts ────────────────────────────────────────────────
    @app.callback(
        Output("high-count",     "children"),
        Output("medium-count",   "children"),
        Output("low-count",      "children"),
        Output("total-count",    "children"),
        Output("priority-pie",   "figure"),
        Output("risk-histogram", "figure"),
        Input("refresh-btn",     "n_clicks"),
        Input("load-trigger",    "data"),
        State("auth-store",      "data"),
        prevent_initial_call=False
    )
    def update_summary(_clicks, _trigger, auth_data):
        if not auth_data or not auth_data.get("token"):
            return "—", "—", "—", "—", empty_fig(), empty_fig()
        try:
            headers      = get_headers(auth_data)
            summary_resp = requests.get(
                f"{API}/priority-summary", headers=headers, timeout=30
            )
            events_resp  = requests.get(
                f"{API}/prioritized", headers=headers, timeout=30
            )
            if summary_resp.status_code != 200 or \
               events_resp.status_code  != 200:
                return "—", "—", "—", "—", empty_fig(), empty_fig()

            s      = summary_resp.json()
            high   = s.get("High",   0)
            medium = s.get("Medium", 0)
            low    = s.get("Low",    0)
            total  = s.get("Total",  0)

            pie = px.pie(
                names  = ["High", "Medium", "Low"],
                values = [high, medium, low],
                color  = ["High", "Medium", "Low"],
                color_discrete_map={
                    "High"  : "#ef4444",
                    "Medium": "#f59e0b",
                    "Low"   : "#10b981"
                }
            ).update_layout(
                paper_bgcolor="#0f172a", font_color="white",
                margin=dict(l=0, r=0, t=20, b=0)
            )

            df = pd.DataFrame(events_resp.json())
            hist = px.histogram(
                df, x="risk_score", nbins=50,
                color_discrete_sequence=["#3b82f6"]
            ).update_layout(
                paper_bgcolor="#0f172a",
                plot_bgcolor ="#0f172a",
                font_color   ="white"
            ) if not df.empty else empty_fig()

            return str(high), str(medium), str(low), str(total), pie, hist

        except Exception as e:
            print(f"update_summary error: {e}")
            return "—", "—", "—", "—", empty_fig(), empty_fig()

    # ── Events table + feature importance ────────────────────────────────────
    @app.callback(
        Output("events-table",             "data"),
        Output("events-table",             "columns"),
        Output("feature-importance-chart", "figure"),
        Input("refresh-btn",               "n_clicks"),
        Input("load-trigger",              "data"),
        Input("priority-filter",           "value"),
        Input("hour-filter",               "value"),
        State("auth-store",                "data"),
        prevent_initial_call=False
    )
    def update_table(_clicks, _trigger, priority_filter, hour_range, auth_data):
        if not auth_data or not auth_data.get("token"):
            return [], [], empty_fig()
        try:
            headers     = get_headers(auth_data)
            events_resp = requests.get(
                f"{API}/prioritized", headers=headers, timeout=30
            )
            imp_resp    = requests.get(
                f"{API}/feature-importance", headers=headers, timeout=10
            )
            if events_resp.status_code != 200:
                return [], [], empty_fig()

            df = pd.DataFrame(events_resp.json())
            if df.empty:
                return [], [], empty_fig()

            if priority_filter and priority_filter != "All" \
                    and "priority" in df.columns:
                df = df[df["priority"] == priority_filter]
            if "hour" in df.columns and hour_range:
                df = df[(df["hour"] >= hour_range[0]) &
                        (df["hour"] <= hour_range[1])]
            if "risk_score" in df.columns:
                df["risk_score"] = df["risk_score"].round(4)

            display_cols = ["event_id", "hour", "day_of_week",
                            "risk_score", "priority"]
            display_cols = [c for c in display_cols if c in df.columns]
            columns      = [{"name": c.replace("_", " ").title(), "id": c}
                            for c in display_cols]
            data         = df[display_cols].to_dict(orient="records")

            bar = empty_fig()
            if imp_resp.status_code == 200:
                imp    = imp_resp.json()
                imp_df = pd.DataFrame(
                    list(imp.items()), columns=["Feature", "Importance"]
                ).sort_values("Importance", ascending=True)
                bar = px.bar(
                    imp_df, x="Importance", y="Feature",
                    orientation="h", color="Importance",
                    color_continuous_scale="Blues"
                ).update_layout(
                    paper_bgcolor="#0f172a",
                    font_color   ="white",
                    height       =400
                )
            return data, columns, bar

        except Exception as e:
            print(f"update_table error: {e}")
            return [], [], empty_fig()

    # ── SHAP ─────────────────────────────────────────────────────────────────
    @app.callback(
        Output("shap-chart",          "figure"),
        Output("shap-interpretation", "children"),
        Input("shap-btn",             "n_clicks"),
        State("shap-index",           "value"),
        State("auth-store",           "data"),
        prevent_initial_call=True
    )
    def update_shap(n_clicks, event_index, auth_data):
        if event_index is None:
            event_index = 0
        try:
            headers = get_headers(auth_data)
            resp    = requests.get(
                f"{API}/shap/event/{event_index}",
                headers=headers, timeout=60
            )
            if resp.status_code == 404:
                return (
                    go.Figure().update_layout(
                        title=f"Event {event_index} Not Found",
                        paper_bgcolor="#0f172a", font_color="white",
                        height=250
                    ),
                    dbc.Alert(f"❌ Event {event_index} not found",
                              color="warning")
                )
            if resp.status_code != 200:
                return (
                    go.Figure().update_layout(
                        title=f"Error {resp.status_code}",
                        paper_bgcolor="#0f172a", font_color="white",
                        height=250
                    ),
                    dbc.Alert("Failed to load SHAP data", color="danger")
                )

            d            = resp.json()
            features     = d.get("feature_names",  [])
            shap_vals    = d.get("shap_values",     [])
            feature_vals = d.get("feature_values",  [])
            interp       = d.get("interpretation",  "")
            pred_label   = d.get("predicted_label", "Unknown")

            if not features:
                return empty_fig(), dbc.Alert("No SHAP data", color="warning")

            paired = sorted(
                zip(features, shap_vals, feature_vals),
                key=lambda x: abs(x[1]), reverse=True
            )[:10]
            f_top, s_top, v_top = zip(*paired)

            fig = go.Figure(go.Bar(
                x           = list(s_top),
                y           = list(f_top),
                orientation = "h",
                marker_color= ["#ef4444" if v > 0 else "#10b981"
                               for v in s_top],
                text        = [f"{v:.3f}" for v in s_top],
                textposition= "outside"
            ))
            fig.update_layout(
                title        = f"Event {event_index}: {pred_label}",
                xaxis_title  = "SHAP Value",
                paper_bgcolor= "#0f172a",
                plot_bgcolor = "#0f172a",
                font_color   = "white",
                height       = 280,
                margin       = dict(l=140, r=40, t=40, b=20)
            )
            return fig, dbc.Alert(interp, color="info")

        except Exception as e:
            print(f"SHAP error: {e}")
            return (
                empty_fig(),
                dbc.Alert(f"Error: {str(e)[:100]}", color="danger")
            )

    # ── Feedback submit ───────────────────────────────────────────────────────
    @app.callback(
        Output("feedback-message", "children"),
        Input("feedback-btn",      "n_clicks"),
        State("shap-index",              "value"),
        State("feedback-correct-label",  "value"),
        State("feedback-correct-flag",   "value"),
        State("feedback-comment",        "value"),
        State("auth-store",              "data"),
        prevent_initial_call=True
    )
    def submit_feedback(n_clicks, event_index, correct_label,
                         correct_flag, comment, auth_data):
        if not auth_data or not auth_data.get("token"):
            return dbc.Alert("Please login to submit feedback", color="warning")
        if event_index is None:
            return dbc.Alert("Enter event index first", color="warning")
        if not correct_label:
            return dbc.Alert("Select correct label", color="warning")
        try:
            headers  = get_headers(auth_data)
            cls_resp = requests.get(
                f"{API}/classification/event/{event_index}",
                headers=headers, timeout=10
            )
            if cls_resp.status_code != 200:
                return dbc.Alert("Could not fetch classification",
                                 color="danger")
            cls     = cls_resp.json()
            fb_resp = requests.post(
                f"{API}/classification/feedback",
                headers=headers,
                json={
                    "event_index"            : event_index,
                    "event_id"               : cls.get("event_id", event_index),
                    "predicted_class"        : cls.get("predicted_class", 0),
                    "predicted_label"        : cls.get("predicted_label",
                                                        "Unknown"),
                    "correct_label"          : correct_label,
                    "analyst_comment"        : comment or "",
                    "is_correctly_classified": correct_flag == "true"
                },
                timeout=10
            )
            if fb_resp.status_code == 200:
                return dbc.Alert(
                    f"✅ Feedback submitted! "
                    f"ID: {fb_resp.json().get('feedback_id')}",
                    color="success"
                )
            return dbc.Alert(
                f"Failed: {fb_resp.json().get('detail', 'Unknown')}",
                color="danger"
            )
        except Exception as e:
            return dbc.Alert(f"Error: {str(e)[:100]}", color="danger")

    # ── Feedback history ──────────────────────────────────────────────────────
    @app.callback(
        Output("feedback-table-container", "children"),
        Input("load-trigger",              "data"),
        Input("refresh-btn",               "n_clicks"),
        State("auth-store",                "data"),
        prevent_initial_call=False
    )
    def load_feedback_history(_trigger, _clicks, auth_data):
        if not auth_data or not auth_data.get("token"):
            return html.P("Login to view feedback history",
                          style={"color": "#94a3b8"})
        try:
            headers = get_headers(auth_data)
            resp    = requests.get(
                f"{API}/classification/feedback/all",
                headers=headers, timeout=10
            )
            if resp.status_code != 200:
                return dbc.Alert("Could not load feedback", color="danger")

            rows = resp.json()
            if not rows:
                return html.P("No feedback yet.",
                              style={"color": "#94a3b8"})

            df   = pd.DataFrame(rows)
            role = auth_data.get("role", "")

            # Admins see all columns including reviewer info
            if role in ["system_admin", "admin"]:
                cols = ["id", "event_index", "predicted_label",
                        "correct_label", "is_correctly_classified",
                        "analyst_username", "submitted_at",
                        "status", "reviewed_by"]
            else:
                # Analysts only see their own submissions
                cols = ["id", "event_index", "predicted_label",
                        "correct_label", "is_correctly_classified",
                        "submitted_at", "status"]

            cols = [c for c in cols if c in df.columns]

            return dash_table.DataTable(
                data   =df[cols].to_dict(orient="records"),
                columns=[{"name": c.replace("_", " ").title(), "id": c}
                         for c in cols],
                page_size=8,
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "#0f172a",
                    "color"          : "#3b82f6",
                    "fontWeight"     : "600",
                    "border"         : "none"
                },
                style_data={
                    "backgroundColor": "#1e293b",
                    "color"          : "#e2e8f0",
                    "border"         : "none"
                },
                style_data_conditional=[
                    {"if": {"filter_query":
                                '{is_correctly_classified} = false'},
                     "backgroundColor": "#7f1a1a",
                     "color"          : "#fca5a5"},
                    {"if": {"filter_query":
                                '{is_correctly_classified} = true'},
                     "backgroundColor": "#064e3b",
                     "color"          : "#6ee7b7"},
                    {"if": {"filter_query": '{status} = "pending"'},
                     "color": "#fcd34d"},
                    {"if": {"filter_query": '{status} = "reviewed"'},
                     "color": "#6ee7b7"},
                ],
                sort_action="native",
            )
        except Exception as e:
            return dbc.Alert(f"Error: {str(e)[:100]}", color="danger")