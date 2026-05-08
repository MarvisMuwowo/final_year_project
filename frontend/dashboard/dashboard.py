from dash import dcc, html, dash_table, Input, Output, State
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
    return dbc.Container([

        # ── Header
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-chart-line",
                           style={"fontSize": "28px", "color": "#3b82f6",
                                  "marginRight": "12px"}),
                    html.H4(
                        "ML-Driven Windows Security Log Prioritization",
                        className="mb-0",
                        style={"color": "#f8fafc", "fontWeight": "bold"}
                    ),
                ], style={"display": "flex", "alignItems": "center"})
            ], width=8),
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-user-circle",
                           style={"fontSize": "18px", "color": "#3b82f6"}),
                    html.Span(f"  {username}",
                              style={"color": "#e2e8f0", "marginLeft": "6px"}),
                    html.Span(f"  [{role}]",
                              style={"color": "#3b82f6", "fontSize": "12px"}),
                    dbc.Button(
                        [html.I(className="fas fa-sign-out-alt"), " Logout"],
                        id="logout-btn", color="danger", size="sm",
                        style={"marginLeft": "15px",
                               "background":
                                   "linear-gradient(135deg, #ef4444, #dc2626)",
                               "border": "none", "borderRadius": "8px"}
                    )
                ], style={"display": "flex", "alignItems": "center",
                           "justifyContent": "flex-end"})
            ], width=4),
        ], className="mb-4",
           style={"padding": "20px 0", "borderBottom": "2px solid #3b82f6"}),

        # ── Summary Cards
        dbc.Row([
            dbc.Col(_stat_card("fas fa-fire",           "#ef4444",
                               "High Priority",   "high-count"),   width=3),
            dbc.Col(_stat_card("fas fa-exclamation-triangle", "#f59e0b",
                               "Medium Priority", "medium-count"), width=3),
            dbc.Col(_stat_card("fas fa-check-circle",   "#10b981",
                               "Low Priority",    "low-count"),    width=3),
            dbc.Col(_stat_card("fas fa-database",       "#3b82f6",
                               "Total Events",    "total-count"),  width=3),
        ], className="mb-4"),

        # ── Charts
        dbc.Row([
            dbc.Col(_chart_card("Priority Distribution",  "priority-pie"),     width=4),
            dbc.Col(_chart_card("Risk Score Distribution","risk-histogram"),    width=4),
            dbc.Col(_chart_card("Feature Importance",     "feature-importance-chart"), width=4),
        ], className="mb-4"),

        # ── Filters
        dbc.Row([dbc.Col([
            _card("🔍 Filters", dbc.Row([
                dbc.Col([
                    html.Label("Priority Level", style={"color": "#e2e8f0"}),
                    dbc.Select(
                        id="priority-filter",
                        options=[
                            {"label": "All Events",       "value": "All"},
                            {"label": "🔴 High Priority", "value": "High"},
                            {"label": "🟡 Medium Priority","value": "Medium"},
                            {"label": "🟢 Low Priority",  "value": "Low"},
                        ],
                        value="All",
                        style={"backgroundColor": "#0f172a",
                               "border": "1px solid #3b82f6", "color": "white"}
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Hour Range (0–23)",
                               style={"color": "#e2e8f0"}),
                    dcc.RangeSlider(
                        id="hour-filter", min=0, max=23, step=1,
                        value=[0, 23],
                        marks={i: str(i) for i in range(0, 24, 4)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], width=5),
                dbc.Col([
                    html.Br(),
                    dbc.Button(
                        [html.I(className="fas fa-sync-alt me-2"), "Refresh Data"],
                        id="refresh-btn", className="w-100",
                        style={"background":
                                   "linear-gradient(135deg, #3b82f6, #2563eb)",
                               "border": "none", "borderRadius": "10px",
                               "fontWeight": "bold", "color": "white"}
                    )
                ], width=3),
            ]))
        ])], className="mb-4"),

        # ── Events Table
        dbc.Row([dbc.Col([
            _card("📋 Prioritized Security Events",
                  dash_table.DataTable(
                      id="events-table",
                      page_size=15,
                      style_table={"overflowX": "auto",
                                   "backgroundColor": "#0f172a"},
                      style_header={"backgroundColor": "#1e293b",
                                    "color": "#3b82f6", "fontWeight": "bold",
                                    "border": "1px solid #334155"},
                      style_data={"backgroundColor": "#0f172a",
                                  "color": "#e2e8f0",
                                  "border": "1px solid #334155"},
                      style_data_conditional=[
                          {"if": {"filter_query": '{priority} = "High"'},
                           "backgroundColor": "#450a0a", "color": "#fca5a5"},
                          {"if": {"filter_query": '{priority} = "Medium"'},
                           "backgroundColor": "#451a03", "color": "#fcd34d"},
                          {"if": {"filter_query": '{priority} = "Low"'},
                           "backgroundColor": "#022c22", "color": "#6ee7b7"},
                      ],
                      sort_action="native", filter_action="native",
                      page_current=0,
                  ))
        ])], className="mb-4"),

        # ── SHAP + Feedback
        dbc.Row([dbc.Col([
            _card("🧠 SHAP Feature Explanation & Analyst Feedback", [

                html.P("Enter an event index to see WHY it was classified "
                       "and give feedback if the classification is wrong.",
                       style={"color": "#94a3b8"}),

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
                                placeholder="Event index...",
                                style={"backgroundColor": "#0f172a",
                                       "color": "white",
                                       "border": "2px solid #3b82f6"}
                            )
                        ])
                    ], width=4),
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="fas fa-chart-bar me-2"),
                             "Explain Event"],
                            id="shap-btn",
                            style={"background":
                                       "linear-gradient(135deg, #06b6d4, #0891b2)",
                                   "border": "none", "borderRadius": "10px",
                                   "fontWeight": "bold", "color": "white",
                                   "width": "100%"}
                        )
                    ], width=3),
                ], className="mb-3"),

                html.Div(id="shap-interpretation", className="mb-2"),
                dcc.Graph(id="shap-chart"),

                html.Hr(style={"borderColor": "#3b82f6", "marginTop": "20px"}),

                # ── Feedback Form
                html.H6("📝 Submit Feedback on Classification",
                        style={"color": "#f59e0b", "marginBottom": "15px"}),
                html.Div(id="feedback-message", className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Correct Label", className="text-white"),
                        dbc.Select(
                            id="feedback-correct-label",
                            options=[{"label": v, "value": v}
                                     for v in CLASS_LABELS.values()],
                            placeholder="Select the correct classification...",
                            style={"backgroundColor": "#0f172a",
                                   "border": "1px solid #f59e0b",
                                   "color": "white"}
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Was it correctly classified?",
                                  className="text-white"),
                        dbc.Select(
                            id="feedback-correct-flag",
                            options=[
                                {"label": "✅ Yes — correctly classified",
                                 "value": "true"},
                                {"label": "❌ No — wrong classification",
                                 "value": "false"},
                            ],
                            value="true",
                            style={"backgroundColor": "#0f172a",
                                   "border": "1px solid #f59e0b",
                                   "color": "white"}
                        )
                    ], width=6),
                ], className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Analyst Comment", className="text-white"),
                        dbc.Textarea(
                            id="feedback-comment",
                            placeholder="Describe why the classification "
                                        "is wrong or any additional context...",
                            rows=3,
                            style={"backgroundColor": "#0f172a",
                                   "border": "1px solid #3b82f6",
                                   "color": "white", "borderRadius": "8px"}
                        )
                    ])
                ], className="mb-3"),

                dbc.Button(
                    [html.I(className="fas fa-paper-plane me-2"),
                     "Submit Feedback"],
                    id="feedback-btn", n_clicks=0,
                    style={"background":
                               "linear-gradient(135deg, #f59e0b, #d97706)",
                           "border": "none", "borderRadius": "10px",
                           "fontWeight": "bold", "color": "white",
                           "padding": "10px 25px"}
                ),
            ])
        ])], className="mb-4"),

        # ── Feedback History (admin only)
        dbc.Row([dbc.Col([
            _card("📊 Feedback History", [
                html.Div(id="feedback-table-container")
            ])
        ])]),

    ], fluid=True, style={"padding": "20px", "minHeight": "100vh"})


# ── LAYOUT HELPERS ────────────────────────────────────────────────────────────
def _stat_card(icon, color, label, count_id):
    return html.Div([
        html.I(className=icon,
               style={"fontSize": "28px", "color": color,
                      "marginBottom": "8px"}),
        html.H5(label, style={"color": color}),
        html.H2(id=count_id, style={"fontSize": "2.5rem",
                                     "fontWeight": "bold", "color": color})
    ], style={
        "background"  : "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
        "borderRadius": "15px", "padding": "20px", "textAlign": "center",
        "border"      : f"1px solid {color}"
    })

def _chart_card(title, graph_id):
    return dbc.Card([
        dbc.CardHeader(html.H5(title, style={"color": "#3b82f6"})),
        dbc.CardBody(dcc.Graph(id=graph_id))
    ], style={
        "background"  : "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
        "border"      : "1px solid #3b82f6",
        "borderRadius": "15px"
    })

def _card(title, content):
    return dbc.Card([
        dbc.CardHeader(html.H5(title, style={"color": "#3b82f6"})),
        dbc.CardBody(content)
    ], style={
        "background"  : "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
        "border"      : "1px solid #3b82f6",
        "borderRadius": "15px"
    })


# ── DASHBOARD CALLBACKS ───────────────────────────────────────────────────────
def register_dashboard_callbacks(app):

    @app.callback(
        Output("auth-store", "data",     allow_duplicate=True),
        Output("url",        "pathname", allow_duplicate=True),
        Input("logout-btn",  "n_clicks"),
        prevent_initial_call=True
    )
    def handle_logout(n_clicks):
        return None, "/"

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
            if summary_resp.status_code != 200 or events_resp.status_code != 200:
                return "—", "—", "—", "—", empty_fig(), empty_fig()

            s      = summary_resp.json()
            high   = s.get("High",   0)
            medium = s.get("Medium", 0)
            low    = s.get("Low",    0)
            total  = s.get("Total",  0)

            pie = px.pie(
                names=["High", "Medium", "Low"],
                values=[high, medium, low],
                color=["High", "Medium", "Low"],
                color_discrete_map={
                    "High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"
                }
            ).update_layout(paper_bgcolor="#0f172a", font_color="white")

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
                    plot_bgcolor ="#0f172a",
                    font_color   ="white",
                    height       =400
                )

            return data, columns, bar

        except Exception as e:
            print(f"update_table error: {e}")
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
        if not auth_data or not auth_data.get("token"):
            return empty_fig(), dbc.Alert(
                "Please log in to view SHAP explanations", color="warning"
            )
        if event_index is None:
            event_index = 0

        try:
            headers  = get_headers(auth_data)
            resp     = requests.get(
                f"{API}/shap/event/{event_index}",
                headers=headers, timeout=60
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

            d            = resp.json()
            features     = d.get("feature_names", [])
            shap_vals    = d.get("shap_values",   [])
            feature_vals = d.get("feature_values", [])
            interpretation_text = d.get("interpretation", "")
            top_features = d.get("top_features", [])

            if not features:
                return empty_fig(), dbc.Alert(
                    "No SHAP data for this event", color="warning"
                )

            sorted_pairs = sorted(
                zip(features, shap_vals, feature_vals),
                key=lambda x: abs(x[1]), reverse=True
            )[:15]
            fs, ss, vs = zip(*sorted_pairs)

            fig = go.Figure(go.Bar(
                x=list(ss),
                y=[f"{f} = {round(v, 2)}" for f, v in zip(fs, vs)],
                orientation="h",
                marker_color=["#ef4444" if v > 0 else "#10b981" for v in ss],
                text=[f"{v:.3f}" for v in ss],
                textposition="outside"
            ))
            fig.update_layout(
                title       =f"SHAP Explanation — Event {event_index}",
                xaxis_title ="SHAP Value  "
                             "(🔴 Positive = increases risk  |  "
                             "🟢 Negative = reduces risk)",
                paper_bgcolor="#0f172a",
                plot_bgcolor ="0f172a",
                font_color   ="white",
                height       =500,
                margin       =dict(l=220, r=60, t=60, b=60)
            )

            interpretation = dbc.Alert([
                html.B("📖 Interpretation:"), html.Br(),
                html.Span(interpretation_text,
                          style={"color": "#e2e8f0"}), html.Br(), html.Br(),
                html.Span("🔴 Red = increases risk  |  ", style={"color": "#ef4444"}),
                html.Span("🟢 Green = reduces risk",     style={"color": "#10b981"}),
            ], color="info")

            return fig, interpretation

        except Exception as e:
            print(f"SHAP error: {e}")
            return empty_fig(), dbc.Alert(f"Error: {str(e)}", color="danger")

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
            return dbc.Alert("Please log in to submit feedback", color="warning")
        if event_index is None:
            return dbc.Alert("Please enter an event index first", color="warning")
        if not correct_label:
            return dbc.Alert(
                "Please select the correct label", color="warning"
            )

        try:
            headers = get_headers(auth_data)

            # Get current classification for this event
            cls_resp = requests.get(
                f"{API}/classification/event/{event_index}",
                headers=headers, timeout=10
            )
            if cls_resp.status_code != 200:
                return dbc.Alert("Could not fetch classification data",
                                 color="danger")

            cls = cls_resp.json()

            feedback_resp = requests.post(
                f"{API}/classification/feedback",
                headers=headers,
                json={
                    "event_index"            : event_index,
                    "event_id"               : cls["event_id"],
                    "predicted_class"        : cls["predicted_class"],
                    "predicted_label"        : cls["predicted_label"],
                    "correct_label"          : correct_label,
                    "analyst_comment"        : comment or "",
                    "is_correctly_classified": correct_flag == "true"
                },
                timeout=10
            )

            if feedback_resp.status_code == 200:
                return dbc.Alert([
                    html.B("✅ Feedback submitted successfully! "),
                    f"Feedback ID: {feedback_resp.json().get('feedback_id')}"
                ], color="success")

            return dbc.Alert(
                f"Failed: {feedback_resp.json().get('detail', 'Unknown error')}",
                color="danger"
            )

        except Exception as e:
            return dbc.Alert(f"Error: {str(e)}", color="danger")

    @app.callback(
        Output("feedback-table-container", "children"),
        Input("load-trigger", "data"),
        Input("refresh-btn",  "n_clicks"),
        State("auth-store",   "data"),
        prevent_initial_call=False
    )
    def load_feedback_history(_trigger, _clicks, auth_data):
        if not auth_data or not auth_data.get("token"):
            return html.P("Log in to view feedback history",
                          style={"color": "#94a3b8"})
        try:
            headers = get_headers(auth_data)
            resp    = requests.get(
                f"{API}/classification/feedback/all",
                headers=headers, timeout=10
            )
            if resp.status_code != 200:
                return dbc.Alert("Could not load feedback history",
                                 color="danger")

            rows = resp.json()
            if not rows:
                return html.P("No feedback submitted yet.",
                              style={"color": "#94a3b8"})

            df   = pd.DataFrame(rows)
            cols = ["id", "event_index", "event_id", "predicted_label",
                    "correct_label", "is_correctly_classified",
                    "analyst_username", "submitted_at", "status"]
            cols = [c for c in cols if c in df.columns]

            return dash_table.DataTable(
                data   =df[cols].to_dict(orient="records"),
                columns=[{"name": c.replace("_", " ").title(), "id": c}
                         for c in cols],
                page_size=10,
                style_table={"overflowX": "auto"},
                style_header={"backgroundColor": "#1e293b",
                              "color": "#3b82f6", "fontWeight": "bold",
                              "border": "1px solid #334155"},
                style_data={"backgroundColor": "#0f172a",
                            "color": "#e2e8f0",
                            "border": "1px solid #334155"},
                style_data_conditional=[
                    {"if": {"filter_query": '{is_correctly_classified} = false'},
                     "backgroundColor": "#450a0a", "color": "#fca5a5"},
                    {"if": {"filter_query": '{status} = "pending"'},
                     "color": "#fcd34d"},
                    {"if": {"filter_query": '{status} = "reviewed"'},
                     "color": "#6ee7b7"},
                ],
                sort_action="native",
            )
        except Exception as e:
            return dbc.Alert(f"Error: {str(e)}", color="danger")