# frontend/dashboard/dashboard.py
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from utils import API, CLASS_LABELS
from components import stat_card, chart_card, events_modal, feedback_history_modal, model_metrics_modal
from callbacks import register_dashboard_callbacks


def dashboard_layout(username, role):
    is_admin = role in ["system_admin", "admin"]

    return dbc.Container([

        # ── Local token store (synced from auth-store on login) ──
        dcc.Store(id="token-store", storage_type="session", data={}),
        dcc.Store(id="model-metrics-store", data={}),

        # ── Header ──
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

        # ── Clickable Stats Cards ──
        dbc.Row([
            dbc.Col(stat_card("🔥", "#ef4444", "High Priority", "high-count", "high-stat-card"), width=3),
            dbc.Col(stat_card("⚠️", "#f59e0b", "Medium Priority", "medium-count", "medium-stat-card"), width=3),
            dbc.Col(stat_card("✅", "#10b981", "Low Priority", "low-count", "low-stat-card"), width=3),
            dbc.Col(stat_card("📊", "#3b82f6", "Total Events", "total-count", "total-stat-card"), width=3),
        ], className="mb-4 g-3"),

        # ── Charts ──
        dbc.Row([
            dbc.Col(chart_card("Priority Distribution", "priority-pie"), width=4),
            dbc.Col(chart_card("Risk Score Distribution", "risk-histogram"), width=4),
            dbc.Col(chart_card("Feature Importance", "feature-importance-chart"), width=4),
        ], className="mb-4 g-3"),

        # ── SHAP + Feedback ──
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
                                        value=1, min=0,
                                        placeholder="Enter Event ID (primary key)",
                                        style={"backgroundColor": "#0f172a",
                                               "border": "1px solid #3b82f6",
                                               "color": "white"}
                                    )
                                ])
                            ], width=7),
                            dbc.Col([
                                dbc.Button(
                                    "Explain", id="shap-btn",
                                    color="info", className="w-100",
                                    style={"backgroundColor": "#0891b2",
                                           "border": "none",
                                           "fontWeight": "500"}
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
                                   "border": "1px solid #f59e0b",
                                   "color": "white",
                                   "marginBottom": "12px"}
                        ),
                        dbc.Label("Was it correctly classified?",
                                  className="mb-1",
                                  style={"color": "#cbd5e1", "fontSize": "12px"}),
                        dbc.Select(
                            id="feedback-correct-flag",
                            options=[
                                {"label": "✅ Yes", "value": "true"},
                                {"label": "❌ No", "value": "false"},
                            ],
                            value="true",
                            style={"backgroundColor": "#0f172a",
                                   "border": "1px solid #f59e0b",
                                   "color": "white",
                                   "marginBottom": "12px"}
                        ),
                        dbc.Label("Analyst Comment", className="mb-1",
                                  style={"color": "#cbd5e1", "fontSize": "12px"}),
                        dbc.Textarea(
                            id="feedback-comment",
                            placeholder="Additional context...",
                            rows=2,
                            style={"backgroundColor": "#0f172a",
                                   "border": "1px solid #3b82f6",
                                   "color": "white",
                                   "borderRadius": "8px",
                                   "marginBottom": "16px"}
                        ),
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="fas fa-paper-plane me-2"),
                                     "Submit Feedback"],
                                    id="feedback-btn", color="warning",
                                    className="w-100",
                                    style={"backgroundColor": "#d97706",
                                           "border": "none",
                                           "fontWeight": "500"}
                                )
                            ], width=6),
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="fas fa-history me-2"),
                                     "View History"],
                                    id="view-feedback-history-btn",
                                    color="info",
                                    className="w-100",
                                    style={"backgroundColor": "#0891b2",
                                           "border": "none",
                                           "fontWeight": "500"}
                                )
                            ], width=6),
                        ]),
                    ])
                ], className="h-100 shadow-sm",
                   style={"backgroundColor": "#1e293b", "border": "none"})
            ], width=6),
        ], className="mb-4 g-3"),

        # ── ADMIN CONTROLS ──
        dbc.Row([
            dbc.Col([
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
                        # ── Model switch buttons with Info ──
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="fas fa-bolt me-2"), "XGBoost"],
                                    id="switch-xgboost-btn", n_clicks=0,
                                    className="w-100",
                                    style={"background": "linear-gradient(135deg, #f59e0b, #d97706)",
                                           "border": "none", "borderRadius": "8px",
                                           "fontWeight": "500", "color": "white"}
                                ),
                                dbc.Button(
                                    [html.I(className="fas fa-info-circle me-1"), "Info"],
                                    id="info-xgboost-btn",
                                    color="secondary",
                                    size="sm",
                                    className="w-100 mt-1",
                                    style={"backgroundColor": "#334155", "border": "none"}
                                )
                            ], width=4),
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="fas fa-tree me-2"), "Random Forest"],
                                    id="switch-rf-btn", n_clicks=0,
                                    className="w-100",
                                    style={"background": "linear-gradient(135deg, #10b981, #059669)",
                                           "border": "none", "borderRadius": "8px",
                                           "fontWeight": "500", "color": "white"}
                                ),
                                dbc.Button(
                                    [html.I(className="fas fa-info-circle me-1"), "Info"],
                                    id="info-rf-btn",
                                    color="secondary",
                                    size="sm",
                                    className="w-100 mt-1",
                                    style={"backgroundColor": "#334155", "border": "none"}
                                )
                            ], width=4),
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="fas fa-cat me-2"), "CatBoost"],
                                    id="switch-catboost-btn", n_clicks=0,
                                    className="w-100",
                                    style={"background": "linear-gradient(135deg, #8b5cf6, #6d28d9)",
                                           "border": "none", "borderRadius": "8px",
                                           "fontWeight": "500", "color": "white"}
                                ),
                                dbc.Button(
                                    [html.I(className="fas fa-info-circle me-1"), "Info"],
                                    id="info-catboost-btn",
                                    color="secondary",
                                    size="sm",
                                    className="w-100 mt-1",
                                    style={"backgroundColor": "#334155", "border": "none"}
                                )
                            ], width=4),
                        ], className="mb-3"),
                        # ── Rebuild Cache button ──
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="fas fa-sync-alt me-2"),
                                     "Rebuild Cache"],
                                    id="rebuild-cache-btn", n_clicks=0,
                                    className="w-100",
                                    style={"background":
                                               "linear-gradient(135deg, #6366f1, #4f46e5)",
                                           "border": "none",
                                           "borderRadius": "8px",
                                           "fontWeight": "500",
                                           "color": "white"}
                                )
                            ], width=6, className="mx-auto"),
                        ], justify="center"),
                        # ── Retrain Models from Feedback button ──
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="fas fa-robot me-2"),
                                     "Retrain Models from Feedback"],
                                    id="retrain-models-btn", n_clicks=0,
                                    className="w-100 mt-3",
                                    style={"background":
                                               "linear-gradient(135deg, #8b5cf6, #6d28d9)",
                                           "border": "none",
                                           "borderRadius": "8px",
                                           "fontWeight": "500",
                                           "color": "white"}
                                )
                            ], width=8, className="mx-auto"),
                        ], justify="center"),
                        html.P(
                            "Retrain all models using analyst feedback. "
                            "This may take several minutes.",
                            style={"color": "#94a3b8", "fontSize": "11px",
                                   "marginTop": "8px", "textAlign": "center"}
                        ),
                    ])
                ], className="shadow-sm mb-4",
                   style={"backgroundColor": "#1e293b",
                          "border": "1px solid #6366f1"})
            ])
        ]) if is_admin else html.Div(
            [
                html.Div(id="active-model-display", style={"display": "none"}),
                html.Div(id="switch-model-message", style={"display": "none"}),
                html.Button(id="switch-xgboost-btn", style={"display": "none"}, n_clicks=0),
                html.Button(id="switch-rf-btn", style={"display": "none"}, n_clicks=0),
                html.Button(id="switch-catboost-btn", style={"display": "none"}, n_clicks=0),
                html.Button(id="rebuild-cache-btn", style={"display": "none"}, n_clicks=0),
                html.Button(id="retrain-models-btn", style={"display": "none"}, n_clicks=0),
                html.Button(id="info-xgboost-btn", style={"display": "none"}, n_clicks=0),
                html.Button(id="info-rf-btn", style={"display": "none"}, n_clicks=0),
                html.Button(id="info-catboost-btn", style={"display": "none"}, n_clicks=0),
            ]
        ),

        # ── Modals ──
        events_modal(),
        feedback_history_modal(),
        model_metrics_modal(),

        # Hidden stores
        dcc.Store(id="modal-priority-store", data=None),

        # Hidden components to keep callbacks alive
        html.Div([
            dcc.Dropdown(id="priority-filter", value="All",
                         options=[{"label": "All Events", "value": "All"}]),
            dcc.RangeSlider(id="hour-filter", min=0, max=23, value=[0, 23]),
            dash_table.DataTable(id="events-table"),
            html.Button(id="refresh-btn", n_clicks=0),
        ], style={"display": "none"}),

        # Hidden container for feedback history
        html.Div(id="feedback-table-container", style={"display": "none"}),

    ], fluid=True,
       style={"padding": "24px", "backgroundColor": "#0f172a",
              "minHeight": "100vh"})