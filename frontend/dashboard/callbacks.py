# callbacks.py
from dash import Input, Output, State, ctx, html
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from utils import API, CLASS_LABELS, get_headers, empty_fig

def register_dashboard_callbacks(app):

    # ── Sync token from auth-store to token-store (preserve if auth-store cleared) ──
    @app.callback(
        Output("token-store", "data"),
        Input("auth-store", "data"),
        State("token-store", "data"),
        prevent_initial_call=False
    )
    def sync_token(auth_data, current_token_data):
        if auth_data and isinstance(auth_data, dict) and auth_data.get("token"):
            return {
                "token": auth_data["token"],
                "username": auth_data.get("username"),
                "role": auth_data.get("role")
            }
        # If auth-store is empty or invalid, keep the current token
        return current_token_data

    # ── Logout ──
    @app.callback(
        Output("auth-store", "data", allow_duplicate=True),
        Output("url", "pathname", allow_duplicate=True),
        Input("logout-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def handle_logout(n_clicks):
        return None, "/"

    # ── Admin: show active model (uses token-store) ──
    @app.callback(
        Output("active-model-display", "children"),
        Input("load-trigger", "data"),
        Input("switch-model-message", "children"),
        State("token-store", "data"),  # <-- changed to token-store
        prevent_initial_call=False
    )
    def show_active_model(_trigger, _msg, token_data):
        if not token_data or not token_data.get("token"):
            return ""
        token = token_data["token"]
        role = token_data.get("role", "")
        if role not in ["system_admin", "admin"]:
            return ""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{API}/active-model", headers=headers, timeout=10)
            if resp.status_code == 200:
                active = resp.json().get("active_model", "xgboost")
                color = "#f59e0b" if active == "xgboost" else "#10b981"
                icon = "fas fa-bolt" if active == "xgboost" else "fas fa-tree"
                return dbc.Alert([
                    html.I(className=f"{icon} me-2"),
                    html.B("Active Model: "),
                    html.Span(
                        active.replace("_", " ").title(),
                        style={"color": color, "fontWeight": "bold"}
                    )
                ], color="dark", style={"border": f"1px solid {color}"})
        except Exception as e:
            print(f"Active model error: {e}")
            return ""

    # ── Admin: switch model / rebuild cache (uses token-store) ──
    @app.callback(
        Output("switch-model-message", "children"),
        Input("switch-xgboost-btn", "n_clicks"),
        Input("switch-rf-btn", "n_clicks"),
        Input("rebuild-cache-btn", "n_clicks"),
        State("token-store", "data"),  # <-- changed to token-store
        prevent_initial_call=True
    )
    def handle_admin_actions(xgb_clicks, rf_clicks, cache_clicks, token_data):
        # --- Debug: print token_data to console ---
        print("\n=== ADMIN ACTION ===")
        print("token_data:", token_data)
        print("triggered:", ctx.triggered_id)
        print("=====================\n")

        # 1. Check authentication
        if not token_data or not token_data.get("token"):
            return dbc.Alert("🔐 Not authenticated (token missing).", color="danger")

        token = token_data["token"]
        role = token_data.get("role", "")

        # 2. Check admin role
        if role not in ["system_admin", "admin"]:
            return dbc.Alert("❌ Admin access required.", color="danger")

        # 3. Determine which button was clicked
        triggered = ctx.triggered_id
        if not triggered:
            return ""

        headers = {"Authorization": f"Bearer {token}"}
        try:
            if triggered == "switch-xgboost-btn":
                url = f"{API}/switch-model/xgboost"
            elif triggered == "switch-rf-btn":
                url = f"{API}/switch-model/random_forest"
            elif triggered == "rebuild-cache-btn":
                url = f"{API}/refresh-cache"
            else:
                return ""

            print(f"POST to {url}")
            resp = requests.post(url, headers=headers, timeout=120)
            print(f"Status: {resp.status_code}, Body: {resp.text}")

            if resp.status_code == 200:
                return dbc.Alert(
                    resp.json().get("message", "Operation completed."),
                    color="success"
                )
            elif resp.status_code == 403:
                return dbc.Alert("❌ Access denied — admin only.", color="danger")
            else:
                detail = resp.json().get("detail", "Unknown error")
                return dbc.Alert(f"❌ {detail}", color="danger")

        except requests.exceptions.ConnectionError:
            return dbc.Alert("🔌 Backend server is not running.", color="danger")
        except Exception as e:
            print(f"Admin error: {e}")
            return dbc.Alert(str(e), color="danger")

    # ── Summary cards & charts ──
    @app.callback(
        Output("high-count", "children"),
        Output("medium-count", "children"),
        Output("low-count", "children"),
        Output("total-count", "children"),
        Output("priority-pie", "figure"),
        Output("risk-histogram", "figure"),
        Input("refresh-btn", "n_clicks"),
        Input("load-trigger", "data"),
        State("auth-store", "data"),
        prevent_initial_call=False
    )
    def update_summary(_clicks, _trigger, auth_data):
        if not auth_data or not auth_data.get("token"):
            return "—", "—", "—", "—", empty_fig(), empty_fig()
        try:
            headers = get_headers(auth_data)
            summary_resp = requests.get(
                f"{API}/priority-summary", headers=headers, timeout=30
            )
            events_resp = requests.get(
                f"{API}/prioritized", headers=headers, timeout=30
            )
            if summary_resp.status_code != 200 or events_resp.status_code != 200:
                return "—", "—", "—", "—", empty_fig(), empty_fig()

            s = summary_resp.json()
            high = s.get("High", 0)
            medium = s.get("Medium", 0)
            low = s.get("Low", 0)
            total = s.get("Total", 0)

            pie = px.pie(
                names=["High", "Medium", "Low"],
                values=[high, medium, low],
                color=["High", "Medium", "Low"],
                color_discrete_map={
                    "High": "#ef4444",
                    "Medium": "#f59e0b",
                    "Low": "#10b981"
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
                plot_bgcolor="#0f172a",
                font_color="white"
            ) if not df.empty else empty_fig()

            return str(high), str(medium), str(low), str(total), pie, hist

        except Exception as e:
            print(f"update_summary error: {e}")
            return "—", "—", "—", "—", empty_fig(), empty_fig()

    # ── Events table & feature importance (hidden, kept for compatibility) ──
    @app.callback(
        Output("events-table", "data"),
        Output("events-table", "columns"),
        Output("feature-importance-chart", "figure"),
        Input("refresh-btn", "n_clicks"),
        Input("load-trigger", "data"),
        Input("priority-filter", "value"),
        Input("hour-filter", "value"),
        State("auth-store", "data"),
        prevent_initial_call=False
    )
    def update_table(_clicks, _trigger, priority_filter, hour_range, auth_data):
        if not auth_data or not auth_data.get("token"):
            return [], [], empty_fig()
        try:
            headers = get_headers(auth_data)
            events_resp = requests.get(
                f"{API}/prioritized", headers=headers, timeout=30
            )
            imp_resp = requests.get(
                f"{API}/feature-importance", headers=headers, timeout=10
            )
            if events_resp.status_code != 200:
                return [], [], empty_fig()

            df = pd.DataFrame(events_resp.json())
            if df.empty:
                return [], [], empty_fig()

            if priority_filter and priority_filter != "All" and "priority" in df.columns:
                df = df[df["priority"] == priority_filter]
            if "hour" in df.columns and hour_range:
                df = df[(df["hour"] >= hour_range[0]) &
                        (df["hour"] <= hour_range[1])]
            if "risk_score" in df.columns:
                df["risk_score"] = df["risk_score"].round(4)

            display_cols = ["event_id", "hour", "day_of_week", "risk_score", "priority"]
            display_cols = [c for c in display_cols if c in df.columns]
            columns = [{"name": c.replace("_", " ").title(), "id": c} for c in display_cols]
            data = df[display_cols].to_dict(orient="records")

            bar = empty_fig()
            if imp_resp.status_code == 200:
                imp = imp_resp.json()
                imp_df = pd.DataFrame(
                    list(imp.items()), columns=["Feature", "Importance"]
                ).sort_values("Importance", ascending=True)
                bar = px.bar(
                    imp_df, x="Importance", y="Feature",
                    orientation="h", color="Importance",
                    color_continuous_scale="Blues"
                ).update_layout(
                    paper_bgcolor="#0f172a",
                    font_color="white",
                    height=400
                )
            return data, columns, bar

        except Exception as e:
            print(f"update_table error: {e}")
            return [], [], empty_fig()

    # ── SHAP explanation ──
    @app.callback(
        Output("shap-chart", "figure"),
        Output("shap-interpretation", "children"),
        Input("shap-btn", "n_clicks"),
        State("shap-index", "value"),
        State("auth-store", "data"),
        prevent_initial_call=True
    )
    def update_shap(n_clicks, event_index, auth_data):
        if event_index is None:
            event_index = 0
        try:
            headers = get_headers(auth_data)
            resp = requests.get(
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
                    dbc.Alert(f"❌ Event {event_index} not found", color="warning")
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

            d = resp.json()
            features = d.get("feature_names", [])
            shap_vals = d.get("shap_values", [])
            feature_vals = d.get("feature_values", [])
            interp = d.get("interpretation", "")
            pred_label = d.get("predicted_label", "Unknown")

            if not features:
                return empty_fig(), dbc.Alert("No SHAP data", color="warning")

            paired = sorted(
                zip(features, shap_vals, feature_vals),
                key=lambda x: abs(x[1]), reverse=True
            )[:10]
            f_top, s_top, v_top = zip(*paired)

            fig = go.Figure(go.Bar(
                x=list(s_top),
                y=list(f_top),
                orientation="h",
                marker_color=["#ef4444" if v > 0 else "#10b981" for v in s_top],
                text=[f"{v:.3f}" for v in s_top],
                textposition="outside"
            ))
            fig.update_layout(
                title=f"Event {event_index}: {pred_label}",
                xaxis_title="SHAP Value",
                paper_bgcolor="#0f172a",
                plot_bgcolor="#0f172a",
                font_color="white",
                height=280,
                margin=dict(l=140, r=40, t=40, b=20)
            )
            return fig, dbc.Alert(interp, color="info")

        except Exception as e:
            print(f"SHAP error: {e}")
            return (
                empty_fig(),
                dbc.Alert(f"Error: {str(e)[:100]}", color="danger")
            )

    # ── Feedback submission (uses token-store) ──
    @app.callback(
        Output("feedback-message", "children"),
        Input("feedback-btn", "n_clicks"),
        State("shap-index", "value"),
        State("feedback-correct-label", "value"),
        State("feedback-correct-flag", "value"),
        State("feedback-comment", "value"),
        State("token-store", "data"),
        prevent_initial_call=True
    )
    def submit_feedback(n_clicks, event_index, correct_label,
                         correct_flag, comment, token_data):
        if not token_data or not token_data.get("token"):
            return dbc.Alert("🔐 Not authenticated. Please log in again.", color="warning")

        token = token_data["token"]
        if event_index is None:
            return dbc.Alert("Enter event index first", color="warning")
        if not correct_label:
            return dbc.Alert("Select correct label", color="warning")

        headers = {"Authorization": f"Bearer {token}"}
        try:
            cls_resp = requests.get(
                f"{API}/classification/event/{event_index}",
                headers=headers, timeout=10
            )
            if cls_resp.status_code != 200:
                return dbc.Alert(f"Could not fetch classification (status {cls_resp.status_code})", color="danger")

            cls = cls_resp.json()
            fb_resp = requests.post(
                f"{API}/classification/feedback",
                headers=headers,
                json={
                    "event_index": event_index,
                    "event_id": cls.get("event_id", event_index),
                    "predicted_class": cls.get("predicted_class", 0),
                    "predicted_label": cls.get("predicted_label", "Unknown"),
                    "correct_label": correct_label,
                    "analyst_comment": comment or "",
                    "is_correctly_classified": correct_flag == "true"
                },
                timeout=10
            )

            if fb_resp.status_code == 200:
                return dbc.Alert(
                    f"✅ Feedback submitted! ID: {fb_resp.json().get('feedback_id')}",
                    color="success"
                )
            else:
                detail = fb_resp.json().get('detail', 'Unknown error')
                return dbc.Alert(f"❌ Failed: {detail}", color="danger")

        except requests.exceptions.ConnectionError:
            return dbc.Alert("🔌 Cannot connect to backend.", color="danger")
        except Exception as e:
            print(f"Feedback error: {e}")
            return dbc.Alert(f"❌ Error: {str(e)[:100]}", color="danger")

    # ── Feedback History Modal: open/close ──
    @app.callback(
        Output("feedback-history-modal", "is_open"),
        Input("view-feedback-history-btn", "n_clicks"),
        Input("close-feedback-modal", "n_clicks"),
        State("feedback-history-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_feedback_modal(view_clicks, close_clicks, is_open):
        triggered_id = ctx.triggered_id
        if triggered_id == "view-feedback-history-btn":
            return True
        if triggered_id == "close-feedback-modal":
            return False
        return is_open

    # ── Populate feedback history table inside the modal (both roles allowed) ──
    @app.callback(
        Output("feedback-modal-table", "data"),
        Output("feedback-modal-table", "columns"),
        Output("feedback-modal-title", "children"),
        Output("feedback-modal-loading", "style"),
        Input("feedback-history-modal", "is_open"),
        State("token-store", "data"),
        prevent_initial_call=True
    )
    def load_feedback_modal_data(is_open, token_data):
        if not is_open:
            return [], [], "Feedback History", {"display": "block"}

        if not token_data or not token_data.get("token"):
            return [], [], "🔐 Not authenticated", {"display": "block"}

        token = token_data["token"]
        headers = {"Authorization": f"Bearer {token}"}
        try:
            resp = requests.get(
                f"{API}/classification/feedback/all",
                headers=headers,
                timeout=10
            )
            if resp.status_code == 403:
                return [], [], "⛔ Access Denied", {"display": "block"}
            if resp.status_code != 200:
                return [], [], f"❌ Error {resp.status_code}", {"display": "block"}

            rows = resp.json()
            if not rows:
                return [], [], "No feedback submitted yet", {"display": "none"}

            df = pd.DataFrame(rows)
            cols = ["id", "event_index", "predicted_label",
                    "correct_label", "is_correctly_classified",
                    "analyst_username", "submitted_at", "status"]
            if "reviewed_by" in df.columns:
                cols.append("reviewed_by")
            cols = [c for c in cols if c in df.columns]

            columns = [{"name": c.replace("_", " ").title(), "id": c} for c in cols]
            data = df[cols].to_dict(orient="records")

            return data, columns, f"📊 Feedback History ({len(data)} entries)", {"display": "none"}

        except Exception as e:
            print(f"Feedback modal error: {e}")
            return [], [], f"Error: {str(e)[:100]}", {"display": "block"}

    # ── Modal: open/close and populate events (using token-store) ──
    @app.callback(
        Output("events-modal", "is_open"),
        Output("events-modal-title", "children"),
        Output("events-modal-table", "data"),
        Output("events-modal-table", "columns"),
        Output("modal-loading", "style"),
        Input("high-stat-card", "n_clicks"),
        Input("medium-stat-card", "n_clicks"),
        Input("low-stat-card", "n_clicks"),
        Input("total-stat-card", "n_clicks"),
        Input("close-events-modal", "n_clicks"),
        State("events-modal", "is_open"),
        State("token-store", "data"),
        prevent_initial_call=True,
    )
    def toggle_priority_modal(high, med, low, total, close_btn, is_open, token_data):
        triggered_id = ctx.triggered_id

        if triggered_id == "close-events-modal":
            return False, "Events", [], [], {"display": "block"}

        if not is_open and triggered_id in [
            "high-stat-card",
            "medium-stat-card",
            "low-stat-card",
            "total-stat-card",
        ]:
            priority_map = {
                "high-stat-card": "High",
                "medium-stat-card": "Medium",
                "low-stat-card": "Low",
                "total-stat-card": "All",
            }
            selected_priority = priority_map.get(triggered_id, "All")

            if not token_data or not token_data.get("token"):
                return (
                    True,
                    "🔐 Auth Token Missing - Re-login required",
                    [],
                    [],
                    {"display": "block"},
                )

            try:
                token = token_data["token"]
                headers = {"Authorization": f"Bearer {token}"}
                resp = requests.get(
                    f"{API}/prioritized", headers=headers, timeout=15
                )

                if resp.status_code == 200:
                    df = pd.DataFrame(resp.json())
                    if not df.empty and selected_priority != "All":
                        df = df[df["priority"] == selected_priority]

                    display_cols = [
                        "event_id",
                        "hour",
                        "day_of_week",
                        "risk_score",
                        "priority",
                    ]
                    columns = [
                        {"name": c.replace("_", " ").title(), "id": c}
                        for c in display_cols
                        if c in df.columns
                    ]
                    data = df.to_dict(orient="records")

                    return (
                        True,
                        f"📊 {selected_priority} Priority Logs View",
                        data,
                        columns,
                        {"display": "none"},
                    )
                else:
                    return (
                        True,
                        f"❌ System Error {resp.status_code}",
                        [],
                        [],
                        {"display": "block"},
                    )
            except Exception as e:
                print(f"Modal Fetch Exception: {e}")
                return (
                    True,
                    "🔌 Service Connection Interrupted",
                    [],
                    [],
                    {"display": "block"},
                )

        return is_open, "Events", [], [], {"display": "block"}