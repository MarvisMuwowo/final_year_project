import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import requests

API = "http://127.0.0.1:8000"


# ── Helper form components (with autocomplete disabled) ───────────────────────
def login_form():
    return html.Div([
        html.Div(id="login-error", className="mb-3"),
        dbc.Label("Username", className="text-white mb-1"),
        dbc.Input(id="login-username", type="text", placeholder="Enter your username",
                  className="mb-3", autocomplete="off",
                  style={"backgroundColor": "#0f172a", "border": "2px solid #3b82f6",
                         "color": "white", "borderRadius": "10px"}),
        dbc.Label("Password", className="text-white mb-1"),
        dbc.Input(id="login-password", type="password", placeholder="Enter your password",
                  className="mb-4", autocomplete="new-password",
                  style={"backgroundColor": "#0f172a", "border": "2px solid #3b82f6",
                         "color": "white", "borderRadius": "10px"}),
        dbc.Button([html.I(className="fas fa-sign-in-alt me-2"), "Login to Dashboard"],
                   id="login-btn", n_clicks=0, className="w-100",
                   style={"background": "linear-gradient(135deg, #3b82f6, #2563eb)",
                          "border": "none", "borderRadius": "10px",
                          "fontWeight": "bold", "padding": "12px", "color": "white"}),
    ])

def register_form():
    return html.Div([
        html.Div(id="register-message", className="mb-3"),
        dbc.Label("Username", className="text-white mb-1"),
        dbc.Input(id="reg-username", type="text", placeholder="Choose a username",
                  className="mb-3", autocomplete="off",
                  style={"backgroundColor": "#0f172a", "border": "2px solid #3b82f6",
                         "color": "white", "borderRadius": "10px"}),
        dbc.Label("Email", className="text-white mb-1"),
        dbc.Input(id="reg-email", type="email", placeholder="Enter your email",
                  className="mb-3", autocomplete="off",
                  style={"backgroundColor": "#0f172a", "border": "2px solid #3b82f6",
                         "color": "white", "borderRadius": "10px"}),
        dbc.Label("Password", className="text-white mb-1"),
        dbc.Input(id="reg-password", type="password", placeholder="Minimum 6 characters",
                  className="mb-3", autocomplete="new-password",
                  style={"backgroundColor": "#0f172a", "border": "2px solid #3b82f6",
                         "color": "white", "borderRadius": "10px"}),
        dbc.Label("Confirm Password", className="text-white mb-1"),
        dbc.Input(id="reg-confirm-password", type="password", placeholder="Confirm your password",
                  className="mb-3", autocomplete="new-password",
                  style={"backgroundColor": "#0f172a", "border": "2px solid #3b82f6",
                         "color": "white", "borderRadius": "10px"}),
        dbc.Label("Role", className="text-white mb-1"),
        dbc.Select(id="reg-role",
                   options=[{"label": "Security Analyst", "value": "security_analyst"},
                            {"label": "System Admin", "value": "system_admin"},
                            {"label": "Admin", "value": "admin"},
                            {"label": "Viewer", "value": "viewer"}],
                   value="security_analyst",
                   style={"backgroundColor": "#0f172a", "border": "2px solid #3b82f6",
                          "color": "white", "borderRadius": "10px", "marginBottom": "20px"}),
        dbc.Button([html.I(className="fas fa-user-plus me-2"), "Create Account"],
                   id="register-btn", n_clicks=0, className="w-100",
                   style={"background": "linear-gradient(135deg, #10b981, #059669)",
                          "border": "none", "borderRadius": "10px",
                          "fontWeight": "bold", "padding": "12px", "color": "white"}),
    ])


# ── Professional Authentication Layout (unchanged) ───────────────────────────
auth_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-shield-alt",
                               style={"fontSize": "60px", "color": "#3b82f6",
                                      "display": "block", "textAlign": "center",
                                      "marginBottom": "15px"}),
                        html.H3("Security Log Prioritization",
                                className="text-center mb-1",
                                style={"color": "#60a5fa", "fontWeight": "bold"}),
                        html.P("CBU — DICT Security Dashboard",
                               className="text-center mb-4",
                               style={"color": "#94a3b8"}),
                    ]),
                    html.Div(id="auth-form-container"),
                    html.Div(id="auth-toggle-link", className="text-center mt-3",
                             style={"color": "#94a3b8"}),
                ])
            ], style={
                "background": "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
                "border": "2px solid #3b82f6",
                "borderRadius": "20px",
                "boxShadow": "0 20px 60px rgba(0,0,0,0.5)",
                "padding": "20px"
            })
        ], width=5, lg=4, md=6)
    ], justify="center", style={"marginTop": "8vh", "padding": "20px"})
], fluid=True, style={"minHeight": "100vh", "backgroundColor": "#0f172a"})


# ── Authentication Callbacks (unchanged) ──────────────────────────────────────
def register_auth_callbacks(app):

    @app.callback(
        Output("auth-form-container", "children"),
        Output("auth-toggle-link", "children"),
        Input("auth-mode", "data"),
        prevent_initial_call=False
    )
    def set_initial_form(mode):
        if mode == "register":
            form = register_form()
            link = html.A("← Back to Login", id="auth-toggle-link", n_clicks=0,
                          style={"cursor": "pointer", "color": "#3b82f6", "textDecoration": "none"})
        else:
            form = login_form()
            link = html.A("Don't have an account? Create one →", id="auth-toggle-link", n_clicks=0,
                          style={"cursor": "pointer", "color": "#3b82f6", "textDecoration": "none"})
        return form, link

    @app.callback(
        Output("auth-mode", "data", allow_duplicate=True),
        Input("auth-toggle-link", "n_clicks"),
        State("auth-mode", "data"),
        prevent_initial_call=True
    )
    def toggle_mode(n_clicks, current_mode):
        if n_clicks is None:
            return dash.no_update
        new_mode = "register" if current_mode == "login" else "login"
        return new_mode

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
            return None, dbc.Alert("Please enter username and password", color="danger")
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
                return None, dbc.Alert("Invalid username or password", color="danger")
        except Exception as e:
            return None, dbc.Alert(f"Cannot reach server: {str(e)}", color="danger")

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
            return dbc.Alert("Please fill all fields", color="danger")
        if password != confirm:
            return dbc.Alert("Passwords do not match", color="danger")
        if len(password) < 6:
            return dbc.Alert("Password must be at least 6 characters", color="danger")
        try:
            resp = requests.post(f"{API}/register",
                                 json={"username": username, "email": email,
                                       "password": password, "role": role},
                                 timeout=30)
            if resp.status_code == 200:
                return dbc.Alert([html.B("✅ Account created! "), "Switch to Login tab."],
                                 color="success")
            detail = resp.json().get("detail", "")
            if "username" in detail.lower():
                return dbc.Alert("Username already exists", color="danger")
            elif "email" in detail.lower():
                return dbc.Alert("Email already registered", color="danger")
            return dbc.Alert(f"Registration failed: {detail}", color="danger")
        except Exception as e:
            return dbc.Alert(f"Cannot reach server: {str(e)}", color="danger")