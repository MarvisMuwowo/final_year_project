import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import requests
import json

API = "http://127.0.0.1:8000"

# ── Login form  ────────────────────────────────
def login_form():
    return html.Div([
        html.Div(id="login-error", className="mb-3"),
        dbc.Label("Username", className="text-white-50 small mb-1", style={"fontWeight": "500"}),
        dbc.Input(id="login-username", type="text", placeholder="Enter your username",
                  className="mb-3 text-white", autocomplete="off",
                  style={"backgroundColor": "#0f172a", "border": "1px solid #334155",
                         "borderRadius": "8px", "padding": "10px 14px"}),
        
        dbc.Label("Password", className="text-white-50 small mb-1", style={"fontWeight": "500"}),
        dbc.Input(id="login-password", type="password", placeholder="Enter your password",
                  className="mb-4 text-white", autocomplete="new-password",
                  style={"backgroundColor": "#0f172a", "border": "1px solid #334155",
                         "borderRadius": "8px", "padding": "10px 14px"}),
        
        dbc.Button([html.I(className="fas fa-sign-in-alt me-2"), "Login to Dashboard"],
                   id="login-btn", n_clicks=0, className="w-100 mb-3",
                   style={"background": "linear-gradient(135deg, #3b82f6, #1d4ed8)",
                          "border": "none", "borderRadius": "8px",
                          "fontWeight": "600", "padding": "12px", "color": "white"}),
    ])

# ── Register form ──────────────────────────────
def register_form():
    return html.Div([
        html.Div(id="register-message", className="mb-3"),
        dbc.Label("Username", className="text-white-50 small mb-1", style={"fontWeight": "500"}),
        dbc.Input(id="reg-username", type="text", placeholder="Choose a username",
                  className="mb-3 text-white", autocomplete="off",
                  style={"backgroundColor": "#0f172a", "border": "1px solid #334155",
                         "borderRadius": "8px", "padding": "10px 14px"}),
        
        dbc.Label("Email", className="text-white-50 small mb-1", style={"fontWeight": "500"}),
        dbc.Input(id="reg-email", type="email", placeholder="Enter your email",
                  className="mb-3 text-white", autocomplete="off",
                  style={"backgroundColor": "#0f172a", "border": "1px solid #334155",
                         "borderRadius": "8px", "padding": "10px 14px"}),
        
        dbc.Label("Password", className="text-white-50 small mb-1", style={"fontWeight": "500"}),
        dbc.Input(id="reg-password", type="password", placeholder="Minimum 6 characters",
                  className="mb-3 text-white", autocomplete="new-password",
                  style={"backgroundColor": "#0f172a", "border": "1px solid #334155",
                         "borderRadius": "8px", "padding": "10px 14px"}),
        
        dbc.Label("Confirm Password", className="text-white-50 small mb-1", style={"fontWeight": "500"}),
        dbc.Input(id="reg-confirm-password", type="password", placeholder="Confirm your password",
                  className="mb-3 text-white", autocomplete="new-password",
                  style={"backgroundColor": "#0f172a", "border": "1px solid #334155",
                         "borderRadius": "8px", "padding": "10px 14px"}),
        
        dbc.Label("Role", className="text-white-50 small mb-1", style={"fontWeight": "500"}),
        dbc.Select(id="reg-role",
                   options=[{"label": "Security Analyst", "value": "security_analyst"},
                            {"label": "System Admin", "value": "system_admin"},
                            {"label": "Admin", "value": "admin"},
                            {"label": "Viewer", "value": "viewer"}],
                   value="security_analyst",
                   style={"backgroundColor": "#0f172a", "border": "1px solid #334155",
                          "color": "white", "borderRadius": "8px", "marginBottom": "24px", "padding": "10px 14px"}),
        
        dbc.Button([html.I(className="fas fa-user-plus me-2"), "Create Account"],
                   id="register-btn", n_clicks=0, className="w-100 mb-3",
                   style={"background": "linear-gradient(135deg, #10b981, #047857)",
                          "border": "none", "borderRadius": "8px",
                          "fontWeight": "600", "padding": "12px", "color": "white"}),
    ])

# ── Layout – no tabs, links always present ──────────────────────────────────
auth_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    # Header
                    html.Div([
                        html.I(className="fas fa-shield-alt",
                               style={"fontSize": "50px", "color": "#3b82f6",
                                      "display": "block", "textAlign": "center",
                                      "marginBottom": "12px"}),
                        html.H3("Security Log Prioritization",
                                className="text-center mb-1",
                                style={"color": "#f8fafc", "fontWeight": "700", "letterSpacing": "0.5px"}),
                        html.P("CBU — DICT Security Dashboard",
                               className="text-center mb-4",
                               style={"color": "#64748b", "fontSize": "14px", "fontWeight": "500"}),
                    ]),
                    
                    # Dynamic form container
                    html.Div(id="auth-content", children=login_form()),
                    
                    # Switch links – always present, visibility toggled
                    html.Div([
                        html.Div([
                            html.Span("Don't have an account? ", style={"color": "#94a3b8", "fontSize": "14px"}),
                            html.A("Sign Up", id="go-to-register", n_clicks=0,
                                   style={"color": "#60a5fa", "textDecoration": "none", "cursor": "pointer",
                                          "fontWeight": "600", "fontSize": "14px"})
                        ], id="switch-to-register-container", className="text-center mt-3"),
                        
                        html.Div([
                            html.Span("Already have an account? ", style={"color": "#94a3b8", "fontSize": "14px"}),
                            html.A("Log In", id="go-to-login", n_clicks=0,
                                   style={"color": "#60a5fa", "textDecoration": "none", "cursor": "pointer",
                                          "fontWeight": "600", "fontSize": "14px"})
                        ], id="switch-to-login-container", className="text-center mt-3", style={"display": "none"}),
                    ])
                ])
            ], style={
                "background": "#1e293b",
                "border": "1px solid #334155",
                "borderRadius": "16px",
                "boxShadow": "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
                "padding": "24px"
            })
        ], xs=11, sm=9, md=7, lg=5, xl=4)
    ], justify="center", style={"alignItems": "center", "minHeight": "100vh"})
], fluid=True, style={"backgroundColor": "#0f172a"})


def register_auth_callbacks(app):
    
    # ── Toggle between Login and Register forms + switch links visibility ──
    @app.callback(
        Output("auth-content", "children"),
        Output("switch-to-register-container", "style"),
        Output("switch-to-login-container", "style"),
        Input("go-to-register", "n_clicks"),
        Input("go-to-login", "n_clicks"),
        prevent_initial_call=True
    )
    def toggle_form(reg_clicks, login_clicks):
        ctx = dash.callback_context
        if not ctx.triggered:
            # fallback – should not happen
            return login_form(), {"display": "block"}, {"display": "none"}
        
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if triggered_id == "go-to-register":
            return (register_form(),
                    {"display": "none"},
                    {"display": "block"})
        else:  # go-to-login
            return (login_form(),
                    {"display": "block"},
                    {"display": "none"})

    # ── Login callback (unchanged) ──────────────────────────────────────
    @app.callback(
        Output("auth-store", "data", allow_duplicate=True),
        Output("login-error", "children"),
        Input("login-btn", "n_clicks"),
        State("login-username", "value"),
        State("login-password", "value"),
        prevent_initial_call=True
    )
    def handle_login(n_clicks, username, password):
        if not username or not password:
            return None, dbc.Alert("Please enter username and password", color="danger", style={"borderRadius": "8px"})
        try:
            resp = requests.post(f"{API}/login",
                                 data={"username": username, "password": password},
                                 headers={"Content-Type": "application/x-www-form-urlencoded"},
                                 timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return {"token": data["access_token"],
                        "username": data["username"],
                        "role": data["role"]}, ""
            else:
                # try to get error detail
                try:
                    error_detail = resp.json().get("detail", "Invalid username or password")
                    if isinstance(error_detail, list):
                        error_detail = "; ".join([str(e) for e in error_detail])
                    elif isinstance(error_detail, dict):
                        error_detail = json.dumps(error_detail)
                except:
                    error_detail = "Invalid username or password"
                return None, dbc.Alert(error_detail, color="danger", style={"borderRadius": "8px"})
        except Exception as e:
            return None, dbc.Alert(f"Cannot reach server: {str(e)}", color="danger", style={"borderRadius": "8px"})

    # ── Register callback with robust error handling ────────────────────
    @app.callback(
        Output("register-message", "children"),
        Input("register-btn", "n_clicks"),
        State("reg-username", "value"),
        State("reg-email", "value"),
        State("reg-password", "value"),
        State("reg-confirm-password", "value"),
        State("reg-role", "value"),
        prevent_initial_call=True
    )
    def handle_register(n_clicks, username, email, password, confirm, role):
        if not all([username, email, password, confirm]):
            return dbc.Alert("Please fill all fields", color="danger", style={"borderRadius": "8px"})
        if password != confirm:
            return dbc.Alert("Passwords do not match", color="danger", style={"borderRadius": "8px"})
        if len(password) < 6:
            return dbc.Alert("Password must be at least 6 characters", color="danger", style={"borderRadius": "8px"})
        try:
            resp = requests.post(f"{API}/register",
                                 json={"username": username, "email": email,
                                       "password": password, "role": role},
                                 timeout=30)
            if resp.status_code == 200:
                return dbc.Alert([html.B("✅ Account created! "), "You can now log in."],
                                 color="success", style={"borderRadius": "8px"})
            else:
                # Parse error detail safely
                try:
                    error_data = resp.json()
                    detail = error_data.get("detail", "Registration failed")
                    # If detail is a list, join it; if dict, stringify; else use as string
                    if isinstance(detail, list):
                        detail = "; ".join([str(item) for item in detail])
                    elif isinstance(detail, dict):
                        detail = json.dumps(detail)
                    else:
                        detail = str(detail)
                except:
                    detail = f"Server responded with status {resp.status_code}"
                
                # Check for known errors
                if "username" in detail.lower():
                    return dbc.Alert("Username already exists", color="danger", style={"borderRadius": "8px"})
                elif "email" in detail.lower():
                    return dbc.Alert("Email already registered", color="danger", style={"borderRadius": "8px"})
                else:
                    return dbc.Alert(f"Registration failed: {detail}", color="danger", style={"borderRadius": "8px"})
        except Exception as e:
            return dbc.Alert(f"Cannot reach server: {str(e)}", color="danger", style={"borderRadius": "8px"})