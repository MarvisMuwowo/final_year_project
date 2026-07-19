# landing.py
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

# ── HELPER FUNCTIONS ───────────────────────────────────────────────────────────────
# (All helpers defined first, before they are used in the layout)

def _section_label(text):
    return html.Div(text,
                    style={"color": "#3b82f6", "fontSize": "12px",
                           "fontWeight": "700", "letterSpacing": "2px",
                           "textTransform": "uppercase",
                           "marginBottom": "16px"})

def _divider():
    return html.Div(style={"width": "1px", "height": "40px",
                            "backgroundColor": "#334155",
                            "margin": "0 32px"})

def _hero_stat(value, label):
    return html.Div([
        html.Div(value, style={"fontSize": "22px", "fontWeight": "800",
                                "color": "white", "lineHeight": "1"}),
        html.Div(label, style={"fontSize": "11px", "color": "#64748b",
                                "marginTop": "4px", "fontWeight": "500"})
    ], style={"textAlign": "center"})

def _hex_to_rgba(hex_color):
    """Convert hex color to r,g,b string for rgba() usage."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"

def _feature_card(icon, color, title, description):
    return html.Div([
        html.Div([
            html.I(className=f"{icon}",
                   style={"fontSize": "22px", "color": color})
        ], style={"width": "48px", "height": "48px",
                  "backgroundColor": f"rgba({_hex_to_rgba(color)},0.1)",
                  "borderRadius": "12px",
                  "display": "flex", "alignItems": "center",
                  "justifyContent": "center", "marginBottom": "20px"}),
        html.H5(title, style={"color": "white", "fontWeight": "600",
                               "marginBottom": "12px", "fontSize": "16px"}),
        html.P(description, style={"color": "#64748b", "fontSize": "14px",
                                    "lineHeight": "1.7", "margin": "0"}),
    ], style={"backgroundColor": "#1e293b",
              "border": f"1px solid #1e293b",
              "borderRadius": "16px", "padding": "28px",
              "textAlign": "left", "height": "100%",
              "transition": "border-color 0.2s",
              "cursor": "default"})

def _pipeline_step(num, icon, color, title, description):
    return html.Div([
        html.Div([
            html.Div(num, style={"position": "absolute", "top": "-8px",
                                  "right": "-8px", "width": "20px",
                                  "height": "20px", "backgroundColor": color,
                                  "borderRadius": "50%", "fontSize": "11px",
                                  "fontWeight": "700", "color": "white",
                                  "display": "flex", "alignItems": "center",
                                  "justifyContent": "center"}),
            html.I(className=icon,
                   style={"fontSize": "24px", "color": color})
        ], style={"width": "56px", "height": "56px",
                  "backgroundColor": f"rgba({_hex_to_rgba(color)},0.1)",
                  "borderRadius": "14px", "display": "flex",
                  "alignItems": "center", "justifyContent": "center",
                  "margin": "0 auto 20px", "position": "relative"}),
        html.H6(title, style={"color": "white", "fontWeight": "600",
                               "marginBottom": "12px", "fontSize": "15px"}),
        html.P(description, style={"color": "#64748b", "fontSize": "13px",
                                    "lineHeight": "1.7", "margin": "0"}),
    ], style={"maxWidth": "220px", "padding": "28px 20px",
              "textAlign": "center"})

def _pipeline_arrow():
    return html.Div([
        html.I(className="fas fa-chevron-right",
               style={"color": "#334155", "fontSize": "20px"})
    ], style={"display": "flex", "alignItems": "center",
              "padding": "0 8px", "marginTop": "-20px"})

def _tech_badge(icon, color, label):
    return html.Div([
        html.I(className=icon,
               style={"fontSize": "20px", "color": color,
                      "marginBottom": "8px"}),
        html.Div(label, style={"fontSize": "13px", "color": "#cbd5e1",
                                "fontWeight": "500"})
    ], style={"display": "flex", "flexDirection": "column",
              "alignItems": "center", "justifyContent": "center",
              "backgroundColor": "#1e293b",
              "border": "1px solid #334155",
              "borderRadius": "12px", "padding": "20px 24px",
              "minWidth": "100px"})

def _about_detail(icon, text):
    return html.Div([
        html.I(className=f"{icon} me-2",
               style={"color": "#3b82f6", "width": "16px"}),
        html.Span(text, style={"color": "#cbd5e1", "fontSize": "14px"})
    ], style={"display": "flex", "alignItems": "center",
              "marginBottom": "12px"})

def _metric_card(value, label, sublabel, color):
    return html.Div([
        html.Div(value, style={"fontSize": "28px", "fontWeight": "800",
                                "color": color, "lineHeight": "1",
                                "marginBottom": "8px"}),
        html.Div(label, style={"fontSize": "13px", "color": "white",
                                "fontWeight": "600", "marginBottom": "4px"}),
        html.Div(sublabel, style={"fontSize": "11px", "color": "#64748b"}),
    ], style={"backgroundColor": "#1e293b",
              "border": f"1px solid {color}22",
              "borderLeft": f"3px solid {color}",
              "borderRadius": "12px", "padding": "20px"})

# ── LANDING PAGE LAYOUT ───────────────────────────────────────────────────────
# (Now all helpers are defined, so layout can safely use them)
landing_layout = html.Div([

    # ── Navigation Bar
    html.Nav([
        html.Div([
            html.Div([
                html.I(className="fas fa-shield-alt",
                       style={"fontSize": "24px", "color": "#3b82f6",
                              "marginRight": "10px"}),
                html.Span("SecureLog AI",
                          style={"fontSize": "20px", "fontWeight": "700",
                                 "color": "white", "letterSpacing": "-0.5px"}),
            ], style={"display": "flex", "alignItems": "center"}),

            html.Div([
                html.A("Features",  href="#features",
                       style={"color": "#94a3b8", "marginRight": "24px",
                              "textDecoration": "none", "fontSize": "14px"}),
                html.A("How It Works", href="#how-it-works",
                       style={"color": "#94a3b8", "marginRight": "24px",
                              "textDecoration": "none", "fontSize": "14px"}),
                html.A("About", href="#about",
                       style={"color": "#94a3b8", "marginRight": "24px",
                              "textDecoration": "none", "fontSize": "14px"}),
                html.A([
                    html.I(className="fas fa-sign-in-alt me-2"),
                    "Login to Dashboard"
                ], id="nav-login-btn", href="/dashboard",
                   style={"backgroundColor": "#3b82f6", "color": "white",
                          "padding": "8px 18px", "borderRadius": "8px",
                          "textDecoration": "none", "fontSize": "14px",
                          "fontWeight": "600"}),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={"maxWidth": "1200px", "margin": "0 auto",
                  "padding": "0 24px", "display": "flex",
                  "justifyContent": "space-between", "alignItems": "center",
                  "height": "64px"})
    ], style={"backgroundColor": "#0f172a",
              "borderBottom": "1px solid #1e293b",
              "position": "sticky", "top": "0", "zIndex": "100"}),

    # ── Hero Section
    html.Section([
        html.Div([

            # ── Badge
            html.Div([
                html.I(className="fas fa-certificate me-2",
                       style={"color": "#3b82f6"}),
                html.Span("CBU DICT Final Year Project 2026",
                          style={"color": "#3b82f6", "fontSize": "13px",
                                 "fontWeight": "600"})
            ], style={"display": "inline-flex", "alignItems": "center",
                      "backgroundColor": "rgba(59,130,246,0.1)",
                      "border": "1px solid rgba(59,130,246,0.3)",
                      "borderRadius": "20px", "padding": "6px 14px",
                      "marginBottom": "32px"}),

            # ── Headline
            html.H1([
                "ML-Driven Windows",
                html.Br(),
                html.Span("Security Log",
                          style={"color": "#3b82f6"}),
                " Prioritization"
            ], style={"fontSize": "clamp(36px, 5vw, 64px)",
                      "fontWeight": "800", "color": "white",
                      "lineHeight": "1.1", "marginBottom": "24px",
                      "letterSpacing": "-2px"}),

            # ── Subheading
            html.P(
                "An intelligent security operations platform that automatically "
                "classifies and ranks Windows Security Event Logs using XGBoost "
                "and Isolation Forest, with SHAP-powered explainability for "
                "every decision.",
                style={"fontSize": "18px", "color": "#94a3b8",
                       "maxWidth": "600px", "lineHeight": "1.7",
                       "marginBottom": "40px"}
            ),

            # ── CTA Buttons
            html.Div([
                html.A([
                    html.I(className="fas fa-rocket me-2"),
                    "Open Dashboard"
                ], href="/dashboard",
                   style={"backgroundColor": "#3b82f6", "color": "white",
                          "padding": "14px 28px", "borderRadius": "10px",
                          "textDecoration": "none", "fontWeight": "700",
                          "fontSize": "15px", "marginRight": "16px",
                          "display": "inline-block",
                          "boxShadow": "0 4px 24px rgba(59,130,246,0.4)"}),
                html.A([
                    html.I(className="fas fa-book me-2"),
                    "View API Docs"
                ], href="http://127.0.0.1:8000/docs", target="_blank",
                   style={"backgroundColor": "transparent",
                          "color": "#e2e8f0",
                          "padding": "14px 28px",
                          "borderRadius": "10px",
                          "textDecoration": "none",
                          "fontWeight": "600",
                          "fontSize": "15px",
                          "border": "1px solid #334155",
                          "display": "inline-block"}),
            ], style={"marginBottom": "60px"}),

            # ── Stats Row
            html.Div([
                _hero_stat("95.33%", "Random Forest Accuracy"),
                _divider(),
                _hero_stat("5",      "Event Classes Classified"),
                _divider(),
                _hero_stat("SHAP",   "Explainable AI"),
                _divider(),
                _hero_stat("Real‑Time", "Log Ingestion"),
            ], style={"display": "flex", "alignItems": "center",
                      "gap": "0", "flexWrap": "wrap",
                      "padding": "24px 32px",
                      "backgroundColor": "#1e293b",
                      "borderRadius": "16px",
                      "border": "1px solid #334155",
                      "maxWidth": "700px"}),

        ], style={"maxWidth": "1200px", "margin": "0 auto",
                  "padding": "100px 24px 80px"})
    ], style={"background":
                  "radial-gradient(ellipse at 20% 50%, "
                  "rgba(59,130,246,0.08) 0%, transparent 60%), "
                  "linear-gradient(180deg, #0f172a 0%, #0c1220 100%)",
              "minHeight": "90vh"}),

    # ── Features Section
    html.Section([
        html.Div([
            _section_label("Features"),
            html.H2("Everything a Security Analyst Needs",
                    style={"fontSize": "clamp(28px,4vw,42px)",
                           "fontWeight": "700", "color": "white",
                           "marginBottom": "16px", "letterSpacing": "-1px"}),
            html.P("Built to address the operational challenge of alert fatigue "
                   "at CBU DICT — powered by machine learning, not manual rules.",
                   style={"color": "#94a3b8", "fontSize": "16px",
                          "marginBottom": "64px", "maxWidth": "560px",
                          "margin": "0 auto 64px"}),

            dbc.Row([
                dbc.Col(_feature_card(
                    "fas fa-brain", "#3b82f6",
                    "ML Classification",
                    "XGBoost and Random Forest classifiers trained on real "
                    "Windows Security Event Logs, achieving 95%+ accuracy "
                    "across 5 event categories."
                ), width=12, md=6, lg=4, className="mb-4"),

                dbc.Col(_feature_card(
                    "fas fa-sort-amount-down", "#f59e0b",
                    "Smart Prioritization",
                    "Isolation Forest behavioural anomaly detection scores "
                    "every event as High, Medium, or Low risk — no manual "
                    "rules, purely data-driven."
                ), width=12, md=6, lg=4, className="mb-4"),

                dbc.Col(_feature_card(
                    "fas fa-lightbulb", "#10b981",
                    "SHAP Explainability",
                    "Every prediction comes with a feature-level explanation "
                    "so analysts understand WHY an event was flagged, closing "
                    "the interpretability gap."
                ), width=12, md=6, lg=4, className="mb-4"),

                dbc.Col(_feature_card(
                    "fas fa-sync-alt", "#6366f1",
                    "Real-Time Pipeline",
                    "Windows Security logs are collected automatically via "
                    "pywin32, inserted into PostgreSQL, and the ML cache "
                    "rebuilds every 2 minutes."
                ), width=12, md=6, lg=4, className="mb-4"),

                dbc.Col(_feature_card(
                    "fas fa-comments", "#ec4899",
                    "Analyst Feedback Loop",
                    "Analysts flag misclassifications directly in the "
                    "dashboard. Feedback is stored and reviewed by admins "
                    "to continuously improve the model."
                ), width=12, md=6, lg=4, className="mb-4"),

                dbc.Col(_feature_card(
                    "fas fa-user-shield", "#f97316",
                    "Role-Based Access",
                    "JWT authentication with Security Analyst and System "
                    "Admin roles. Admins can switch models and rebuild the "
                    "ML cache — analysts cannot."
                ), width=12, md=6, lg=4, className="mb-4"),
            ]),
        ], style={"maxWidth": "1200px", "margin": "0 auto",
                  "padding": "100px 24px", "textAlign": "center"})
    ], id="features", style={"backgroundColor": "#0c1220"}),

    # ── How It Works Section
    html.Section([
        html.Div([
            _section_label("How It Works"),
            html.H2("The End-to-End Pipeline",
                    style={"fontSize": "clamp(28px,4vw,42px)",
                           "fontWeight": "700", "color": "white",
                           "marginBottom": "16px", "letterSpacing": "-1px"}),
            html.P("From raw Windows Security event to analyst-ready "
                   "prioritized dashboard — fully automated.",
                   style={"color": "#94a3b8", "fontSize": "16px",
                          "marginBottom": "64px"}),

            html.Div([
                _pipeline_step("1", "fas fa-windows", "#3b82f6",
                               "Windows Security Auditing",
                               "Microsoft Windows generates Security Event "
                               "Logs (logon, account changes, privilege use) "
                               "captured by the built-in auditing framework."),
                _pipeline_arrow(),
                _pipeline_step("2", "fas fa-database", "#f59e0b",
                               "Automated Collection",
                               "A scheduled task runs every 2 minutes, reads "
                               "new events via pywin32, and inserts them into "
                               "PostgreSQL — skipping duplicates automatically."),
                _pipeline_arrow(),
                _pipeline_step("3", "fas fa-cogs", "#10b981",
                               "ML Processing",
                               "process_data() preprocesses the full events "
                               "table. XGBoost classifies each event. "
                               "Isolation Forest scores behavioural anomalies "
                               "and assigns High/Medium/Low priority."),
                _pipeline_arrow(),
                _pipeline_step("4", "fas fa-chart-line", "#6366f1",
                               "Live Dashboard",
                               "The Plotly Dash dashboard polls every 30 "
                               "seconds. Charts, cards, and SHAP explanations "
                               "update automatically — no manual refresh needed."),
            ], style={"display": "flex", "alignItems": "flex-start",
                      "justifyContent": "center", "flexWrap": "wrap",
                      "gap": "0"}),

        ], style={"maxWidth": "1200px", "margin": "0 auto",
                  "padding": "100px 24px", "textAlign": "center"})
    ], id="how-it-works",
       style={"background":
                  "radial-gradient(ellipse at 80% 50%, "
                  "rgba(99,102,241,0.07) 0%, transparent 60%), "
                  "#0f172a"}),

    # ── Tech Stack Section
    html.Section([
        html.Div([
            
            html.H2("Technology Stack",
                    style={"fontSize": "clamp(28px,4vw,42px)",
                           "fontWeight": "700", "color": "white",
                           "marginBottom": "64px",
                           "letterSpacing": "-1px"}),

            html.Div([
                _tech_badge("fas fa-robot",       "#f59e0b", "XGBoost"),
                _tech_badge("fas fa-tree",         "#10b981", "Random Forest"),
                _tech_badge("fas fa-cat",          "#8b5cf6", "CatBoost"),   # ← ADDED
                _tech_badge("fas fa-project-diagram","#3b82f6","SHAP"),
                _tech_badge("fas fa-server",       "#6366f1", "FastAPI"),
                _tech_badge("fas fa-chart-bar",    "#ec4899", "Plotly Dash"),
                _tech_badge("fas fa-database",     "#f97316", "PostgreSQL"),
                _tech_badge("fab fa-python",       "#3b82f6", "Python 3.12"),
                _tech_badge("fas fa-shield-alt",   "#10b981", "pywin32"),
            ], style={"display": "flex", "flexWrap": "wrap",
                      "gap": "16px", "justifyContent": "center"}),
        ], style={"maxWidth": "1200px", "margin": "0 auto",
                  "padding": "100px 24px", "textAlign": "center"})
    ], style={"backgroundColor": "#0c1220"}),

    # ── About Section
    html.Section([
        html.Div([
            dbc.Row([
                dbc.Col([
                    _section_label("About"),
                    html.H2("Final Year Project",
                            style={"fontSize": "clamp(28px,4vw,42px)",
                                   "fontWeight": "700", "color": "white",
                                   "marginBottom": "24px",
                                   "letterSpacing": "-1px"}),
                    html.P(
                        "This system is developed to address the operational "
                        "challenge of alert fatigue at the Directorate of "
                        "Information and Communication Technology (DICT) at "
                        "The Copperbelt University — where the high-volume, "
                        "undifferentiated output of Microsoft Windows Security "
                        "Auditing overwhelmed manual triage.",
                        style={"color": "#94a3b8", "lineHeight": "1.8",
                               "marginBottom": "20px"}
                    ),
                    html.P(
                        "The system classifies and ranks events using supervised "
                        "machine learning (XGBoost,Random Forest or CatBoost), provides "
                        "SHAP-based feature explanations for every decision, "
                        "and surfaces results through a real-time Plotly Dash "
                        "analyst dashboard  ",
                        style={"color": "#94a3b8", "lineHeight": "1.8",
                               "marginBottom": "32px"}
                    ),
                    html.Div([
                        _about_detail("fas fa-user-graduate", "Marvis Muwowo"),
                        _about_detail("fas fa-id-card",       "22179298"),
                        _about_detail("fas fa-university",    "Copperbelt University"),
                        _about_detail("fas fa-building",      "Computer Science Department"),
                        _about_detail("fas fa-chalkboard-teacher",
                                      "Supervised by Mrs. Z.L. Daka"),
                        _about_detail("fas fa-calendar",      "2026"),
                    ]),
                ], width=12, lg=6),

                dbc.Col([
                    html.Div([
                        _metric_card("95.33%", "Classification Accuracy",
                                     "Exceeds 80% proposal target", "#3b82f6"),
                        _metric_card("0.93",   "Macro F1-Score",
                                     "Balanced across all 5 classes", "#10b981"),
                        _metric_card("5",      "Event Categories",
                                     "Logon, Special Logon, UAM, Auditing, Other",
                                     "#f59e0b"),
                        _metric_card("1,496",  "Training Records",
                                     "Real CBU DICT Security events", "#6366f1"),
                    ], style={"display": "grid",
                              "gridTemplateColumns": "1fr 1fr",
                              "gap": "16px"})
                ], width=12, lg=6, className="mt-4 mt-lg-0"),
            ])
        ], style={"maxWidth": "1200px", "margin": "0 auto",
                  "padding": "100px 24px"})
    ], id="about",
       style={"background":
                  "radial-gradient(ellipse at 20% 80%, "
                  "rgba(59,130,246,0.06) 0%, transparent 60%), "
                  "#0f172a"}),

    # ── CTA Banner
    html.Section([
        html.Div([
            html.H2("Ready to explore the dashboard?",
                    style={"fontSize": "clamp(24px,3vw,36px)",
                           "fontWeight": "700", "color": "white",
                           "marginBottom": "16px",
                           "letterSpacing": "-1px"}),
            html.P("Login to view real-time prioritized security events, "
                   "SHAP explanations, and analyst feedback.",
                   style={"color": "#94a3b8", "fontSize": "16px",
                          "marginBottom": "32px"}),
            html.A([
                html.I(className="fas fa-rocket me-2"),
                "Open Dashboard"
            ], href="/dashboard",
               style={"backgroundColor": "#3b82f6", "color": "white",
                      "padding": "14px 32px", "borderRadius": "10px",
                      "textDecoration": "none", "fontWeight": "700",
                      "fontSize": "15px",
                      "boxShadow": "0 4px 24px rgba(59,130,246,0.4)",
                      "display": "inline-block"}),
        ], style={"maxWidth": "600px", "margin": "0 auto",
                  "textAlign": "center", "padding": "80px 24px"})
    ], style={"backgroundColor": "#0c1220",
              "borderTop": "1px solid #1e293b"}),

    # ── Footer
    html.Footer([
        html.Div([
            html.Div([
                html.I(className="fas fa-shield-alt",
                       style={"fontSize": "18px", "color": "#3b82f6",
                              "marginRight": "8px"}),
                html.Span("SecureLog AI",
                          style={"color": "#64748b", "fontSize": "14px"}),
            ], style={"display": "flex", "alignItems": "center",
                      "marginBottom": "8px"}),
            html.P(
                "ML-Driven Windows Security Event Log Prioritization System "
                "— CBU DICT | Computer Science Final Year Project 2026",
                style={"color": "#475569", "fontSize": "12px",
                       "margin": "0"}
            ),
        ], style={"maxWidth": "1200px", "margin": "0 auto",
                  "padding": "32px 24px", "textAlign": "center"})
    ], style={"backgroundColor": "#0a0f1a",
              "borderTop": "1px solid #1e293b"}),

], style={"backgroundColor": "#0f172a", "fontFamily":
              "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"})


# ── LANDING CALLBACKS ───────────────────────────────────────────────────────────
def register_landing_callbacks(app):
    pass