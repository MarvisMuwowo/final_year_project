import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import requests

API = "http://127.0.0.1:8000"


# ── LOGIN & REGISTER LAYOUT ───────────────────────────────────────────────────
auth_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([

                    # ── Header
                    html.Div([
                        html.I(
                            className="fas fa-shield-alt",
                            style={"fontSize": "60px", "color": "#3b82f6",
                                   "display": "block", "textAlign": "center",
                                   "marginBottom": "15px"}
                        ),
                        html.H3(
                            "Security Log Prioritization System",
                            className="text-center mb-1",
                            style={"color": "#60a5fa", "fontWeight": "bold"}
                        ),
                        html.P(
                            "CBU — DICT Security Dashboard",
                            className="text-center mb-4",
                            style={"color": "#94a3b8"}
                        ),
                    ]),

                    # ── Tabs
                    dbc.Tabs([

                        # ── LOGIN TAB
                        dbc.Tab(label="🔐 Login", tab_id="login-tab", children=[
                            html.Br(),
                            html.Div(id="login-error", className="mb-3"),

                            dbc.Label("Username", className="text-white mb-1"),
                            dbc.Input(
                                id="login-username", type="text",
                                placeholder="Enter your username",
                                className="mb-3",
                                style={"backgroundColor": "#0f172a",
                                       "border": "2px solid #3b82f6",
                                       "color": "white", "borderRadius": "10px"}
                            ),

                            dbc.Label("Password", className="text-white mb-1"),
                            dbc.Input(
                                id="login-password", type="password",
                                placeholder="Enter your password",
                                className="mb-4",
                                style={"backgroundColor": "#0f172a",
                                       "border": "2px solid #3b82f6",
                                       "color": "white", "borderRadius": "10px"}
                            ),

                            dbc.Button(
                                [html.I(className="fas fa-sign-in-alt me-2"),
                                 "Login to Dashboard"],
                                id="login-btn", n_clicks=0,
                                className="w-100",
                                style={"background":
                                           "linear-gradient(135deg, #3b82f6, #2563eb)",
                                       "border": "none", "borderRadius": "10px",
                                       "fontWeight": "bold", "padding": "12px",
                                       "color": "white"}
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
                                className="mb-3",
                                style={"backgroundColor": "#0f172a",
                                       "border": "2px solid #3b82f6",
                                       "color": "white", "borderRadius": "10px"}
                            ),

                            dbc.Label("Email", className="text-white mb-1"),
                            dbc.Input(
                                id="reg-email", type="email",
                                placeholder="Enter your email",
                                className="mb-3",
                                style={"backgroundColor": "#0f172a",
                                       "border": "2px solid #3b82f6",
                                       "color": "white", "borderRadius": "10px"}
                            ),

                            dbc.Label("Password", className="text-white mb-1"),
                            dbc.Input(
                                id="reg-password", type="password",
                                placeholder="Minimum 6 characters",
                                className="mb-3",
                                style={"backgroundColor": "#0f172a",
                                       "border": "2px solid #3b82f6",
                                       "color": "white", "borderRadius": "10px"}
                            ),

                            dbc.Label("Confirm Password", className="text-white mb-1"),
                            dbc.Input(
                                id="reg-confirm-password", type="password",
                                placeholder="Confirm your password",
                                className="mb-3",
                                style={"backgroundColor": "#0f172a",
                                       "border": "2px solid #3b82f6",
                                       "color": "white", "borderRadius": "10px"}
                            ),

                            dbc.Label("Role", className="text-white mb-1"),
                            dbc.Select(
                                id="reg-role",
                                options=[
                                    {"label": "Security Analyst",
                                     "value": "security_analyst"},
                                    {"label": "System Admin",
                                     "value": "system_admin"},
                                ],
                                value="security_analyst",
                                style={"backgroundColor": "#0f172a",
                                       "border": "2px solid #3b82f6",
                                       "color": "white", "borderRadius": "10px",
                                       "marginBottom": "20px"}
                            ),

                            dbc.Button(
                                [html.I(className="fas fa-user-plus me-2"),
                                 "Create Account"],
                                id="register-btn", n_clicks=0,
                                className="w-100",
                                style={"background":
                                           "linear-gradient(135deg, #10b981, #059669)",
                                       "border": "none", "borderRadius": "10px",
                                       "fontWeight": "bold", "padding": "12px",
                                       "color": "white"}
                            ),
                        ]),

                    ], active_tab="login-tab"),

                    html.Hr(style={"borderColor": "#3b82f6", "marginTop": "20px"}),
                    html.P(
                        "Powered by Machine Learning | CBU DICT Security Operations",
                        className="text-center mt-2",
                        style={"color": "#64748b", "fontSize": "11px"}
                    )
                ])
            ], style={
                "background"  : "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
                "border"      : "2px solid #3b82f6",
                "borderRadius": "20px",
                "boxShadow"   : "0 20px 60px rgba(0,0,0,0.5)",
                "padding"     : "10px"
            })
        ], width=5, lg=4, md=6)
    ], justify="center", style={"marginTop": "8vh", "padding": "20px"})
], fluid=True, style={"minHeight": "100vh"})


# ── AUTH CALLBACKS ────────────────────────────────────────────────────────────
def register_auth_callbacks(app):

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
            return None, dbc.Alert(
                "Please enter username and password", color="danger"
            )
        try:
            response = requests.post(
                f"{API}/login",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "token"   : data["access_token"],
                    "username": data["username"],
                    "role"    : data["role"]
                }, ""
            elif response.status_code == 401:
                return None, dbc.Alert(
                    "Invalid username or password", color="danger"
                )
            elif response.status_code == 403:
                return None, dbc.Alert("Account is disabled", color="danger")
            else:
                return None, dbc.Alert(
                    f"Login failed: {response.text}", color="danger"
                )
        except Exception as e:
            return None, dbc.Alert(
                f"Cannot reach server: {str(e)}", color="danger"
            )

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
    def handle_register(n_clicks, username, email,
                         password, confirm_password, role):
        if not all([username, email, password, confirm_password]):
            return dbc.Alert("Please fill in all fields", color="danger")
        if password != confirm_password:
            return dbc.Alert("Passwords do not match", color="danger")
        if len(password) < 6:
            return dbc.Alert(
                "Password must be at least 6 characters", color="danger"
            )
        if len(password.encode("utf-8")) > 72:
            return dbc.Alert(
                "Password too long — maximum 72 characters", color="danger"
            )
        try:
            response = requests.post(
                f"{API}/register",
                json={"username": username, "email": email,
                      "password": password, "role": role},
                timeout=30
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
            return dbc.Alert(
                f"Registration failed: {detail}", color="danger"
            )
        except Exception as e:
            return dbc.Alert(
                f"Cannot reach server: {str(e)}", color="danger"
            )