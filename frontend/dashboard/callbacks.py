# frontend/dashboard/callbacks.py
from dash import Input, Output, State, ctx, html, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from utils import API, CLASS_LABELS, get_headers, empty_fig
from dash.exceptions import PreventUpdate


def register_dashboard_callbacks(app):

    # ── Sync token ──
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

    # ── Admin: show active model ──
    @app.callback(
        Output("active-model-display", "children"),
        Input("load-trigger", "data"),
        Input("switch-model-message", "children"),
        State("token-store", "data"),
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
                color_map = {
                    "xgboost": "#f59e0b",
                    "random_forest": "#10b981",
                    "catboost": "#8b5cf6"
                }
                icon_map = {
                    "xgboost": "fas fa-bolt",
                    "random_forest": "fas fa-tree",
                    "catboost": "fas fa-cat"
                }
                color = color_map.get(active, "#f59e0b")
                icon = icon_map.get(active, "fas fa-bolt")
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

    # ── Admin: switch model / rebuild cache / retrain ──
    @app.callback(
        Output("switch-model-message", "children"),
        Input("switch-xgboost-btn", "n_clicks"),
        Input("switch-rf-btn", "n_clicks"),
        Input("switch-catboost-btn", "n_clicks"),
        Input("rebuild-cache-btn", "n_clicks"),
        Input("retrain-models-btn", "n_clicks"),
        State("token-store", "data"),
        prevent_initial_call=True
    )
    def handle_admin_actions(xgb_clicks, rf_clicks, cat_clicks, cache_clicks, retrain_clicks, token_data):
        if not token_data or not token_data.get("token"):
            return dbc.Alert("🔐 Not authenticated.", color="danger")

        token = token_data["token"]
        role = token_data.get("role", "")
        if role not in ["system_admin", "admin"]:
            return dbc.Alert("❌ Admin access required.", color="danger")

        triggered = ctx.triggered_id
        if not triggered:
            return ""

        headers = {"Authorization": f"Bearer {token}"}
        try:
            if triggered == "switch-xgboost-btn":
                url = f"{API}/switch-model/xgboost"
                resp = requests.post(url, headers=headers, timeout=120)
            elif triggered == "switch-rf-btn":
                url = f"{API}/switch-model/random_forest"
                resp = requests.post(url, headers=headers, timeout=120)
            elif triggered == "switch-catboost-btn":
                url = f"{API}/switch-model/catboost"
                resp = requests.post(url, headers=headers, timeout=120)
            elif triggered == "rebuild-cache-btn":
                url = f"{API}/refresh-cache"
                resp = requests.post(url, headers=headers, timeout=120)
            elif triggered == "retrain-models-btn":
                url = f"{API}/retrain-models"
                resp = requests.post(url, headers=headers, timeout=600)
            else:
                return ""

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    return dbc.Alert(data.get("message", "Operation completed."), color="success")
                except ValueError:
                    return dbc.Alert(f"Operation completed (raw): {resp.text[:200]}", color="success")
            elif resp.status_code == 403:
                return dbc.Alert("❌ Access denied — admin only.", color="danger")
            else:
                try:
                    detail = resp.json().get("detail", resp.text)
                except ValueError:
                    detail = resp.text
                return dbc.Alert(f"❌ Error {resp.status_code}: {detail[:200]}", color="danger")

        except requests.exceptions.ConnectionError:
            return dbc.Alert("🔌 Backend server is not running.", color="danger")
        except Exception as e:
            return dbc.Alert(str(e), color="danger")

    # ── Model metrics: open modal and set store ──
    @app.callback(
        Output("model-metrics-store", "data"),
        Output("model-metrics-modal", "is_open"),
        Input("info-xgboost-btn", "n_clicks"),
        Input("info-rf-btn", "n_clicks"),
        Input("info-catboost-btn", "n_clicks"),
        Input("close-model-metrics-modal", "n_clicks"),
        State("model-metrics-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_model_metrics_modal(xgb_clicks, rf_clicks, cat_clicks, close_clicks, is_open):
        triggered_id = ctx.triggered_id
        if triggered_id == "close-model-metrics-modal":
            return {}, False
        if triggered_id == "info-xgboost-btn":
            return {"model": "xgboost"}, True
        if triggered_id == "info-rf-btn":
            return {"model": "random_forest"}, True
        if triggered_id == "info-catboost-btn":
            return {"model": "catboost"}, True
        return {}, is_open

    # ── Load model metrics ──
    @app.callback(
        Output("model-metrics-title", "children"),
        Output("model-metrics-body", "children"),
        Input("model-metrics-store", "data"),
        State("token-store", "data"),
        prevent_initial_call=True
    )
    def load_model_metrics(store_data, token_data):
        if not store_data or not store_data.get("model"):
            return "Model Metrics", html.Div("No model selected")
        if not token_data or not token_data.get("token"):
            return "Model Metrics", dbc.Alert("Not authenticated", color="danger")

        model_name = store_data["model"]
        headers = {"Authorization": f"Bearer {token_data['token']}"}
        try:
            resp = requests.get(f"{API}/model-metrics/{model_name}", headers=headers, timeout=30)
            if resp.status_code == 200:
                metrics = resp.json()
                title = f"📊 {model_name.replace('_', ' ').title()} Metrics"
                rows = []
                rows.append(html.Tr([html.Td("Accuracy", style={"fontWeight": "bold"}), html.Td(f"{metrics['accuracy']:.4f}")]))
                rows.append(html.Tr([html.Td("Macro F1", style={"fontWeight": "bold"}), html.Td(f"{metrics['macro_f1']:.4f}")]))
                rows.append(html.Tr([html.Td("Weighted F1", style={"fontWeight": "bold"}), html.Td(f"{metrics['weighted_f1']:.4f}")]))
                rows.append(html.Tr([html.Td("Test Size", style={"fontWeight": "bold"}), html.Td(str(metrics['test_size']))]))

                per_class = metrics.get("per_class", {})
                for cls_name, cls_metrics in per_class.items():
                    rows.append(html.Tr([
                        html.Td(f"Class: {cls_name}", style={"fontWeight": "bold", "colSpan": 2})
                    ], style={"backgroundColor": "#1e293b"}))
                    rows.append(html.Tr([
                        html.Td("Precision", style={"paddingLeft": "20px"}),
                        html.Td(f"{cls_metrics.get('precision', 0):.4f}")
                    ]))
                    rows.append(html.Tr([
                        html.Td("Recall", style={"paddingLeft": "20px"}),
                        html.Td(f"{cls_metrics.get('recall', 0):.4f}")
                    ]))
                    rows.append(html.Tr([
                        html.Td("F1-Score", style={"paddingLeft": "20px"}),
                        html.Td(f"{cls_metrics.get('f1-score', 0):.4f}")
                    ]))
                    rows.append(html.Tr([
                        html.Td("Support", style={"paddingLeft": "20px"}),
                        html.Td(str(cls_metrics.get('support', 0)))
                    ]))

                body = html.Table([
                    html.Thead(html.Tr([html.Th("Metric"), html.Th("Value")])),
                    html.Tbody(rows)
                ], className="table table-dark table-hover", style={"width": "100%", "borderRadius": "8px", "overflow": "hidden"})
                return title, body
            else:
                try:
                    error_detail = resp.json().get("detail", resp.text)
                except:
                    error_detail = resp.text
                return f"Error loading metrics for {model_name}", dbc.Alert(f"API error (status {resp.status_code}): {error_detail[:200]}", color="danger")
        except Exception as e:
            return "Error", dbc.Alert(str(e), color="danger")

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
        Input("auto-refresh", "n_intervals"),
        State("token-store", "data"),
        prevent_initial_call=False
    )
    def update_summary(_clicks, _trigger, _interval, token_data):
        if not token_data or not token_data.get("token"):
            return "—", "—", "—", "—", empty_fig(), empty_fig()

        token = token_data["token"]
        headers = {"Authorization": f"Bearer {token}"}

        try:
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
                paper_bgcolor="#0f172a",
                font_color="white",
                margin=dict(l=0, r=0, t=20, b=0)
            )

            df = pd.DataFrame(events_resp.json())
            if not df.empty and "risk_score" in df.columns:
                hist = px.histogram(
                    df, x="risk_score", nbins=50,
                    color_discrete_sequence=["#3b82f6"]
                ).update_layout(
                    paper_bgcolor="#0f172a",
                    plot_bgcolor="#0f172a",
                    font_color="white"
                )
            else:
                hist = empty_fig()

            return str(high), str(medium), str(low), str(total), pie, hist

        except Exception as e:
            print(f"update_summary error: {e}")
            return "—", "—", "—", "—", empty_fig(), empty_fig()

    # ── Timeline ──
    @app.callback(
        Output("timeline-chart", "figure"),
        Input("refresh-btn", "n_clicks"),
        Input("load-trigger", "data"),
        Input("auto-refresh", "n_intervals"),
        State("token-store", "data"),
        prevent_initial_call=False
    )
    def update_timeline(_clicks, _trigger, _interval, token_data):
        blank = go.Figure().update_layout(
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            font_color="white",
            height=300
        )
        if not token_data or not token_data.get("token"):
            return blank.update_layout(title="Please log in")

        headers = {"Authorization": f"Bearer {token_data['token']}"}
        try:
            resp = requests.get(f"{API}/prioritized", headers=headers, timeout=30)
            if resp.status_code != 200:
                return blank.update_layout(title=f"Error loading data: {resp.status_code}")

            df = pd.DataFrame(resp.json())
            if df.empty:
                return blank.update_layout(title="No events available")

            high_df = df[df["priority"] == "High"].copy()
            if high_df.empty:
                return blank.update_layout(title="No High priority events")

            if "logged" not in high_df.columns:
                return blank.update_layout(title="Timestamp data missing")

            high_df["logged"] = pd.to_datetime(high_df["logged"])
            high_df = high_df.sort_values("logged")

            fig = px.scatter(
                high_df,
                x="logged",
                y=[1] * len(high_df),
                color="status" if "status" in high_df.columns else None,
                hover_data={
                    "event_id": True,
                    "risk_score": True,
                    "status": True if "status" in high_df.columns else False,
                    "logged": True
                },
                title="High Priority Events Over Time",
                labels={"x": "Time", "y": ""},
                color_discrete_map={
                    "unassigned": "#94a3b8",
                    "in_progress": "#f59e0b",
                    "resolved": "#10b981"
                },
                size_max=12
            )
            fig.update_yaxis(showticklabels=False, showgrid=False)
            fig.update_xaxis(
                showgrid=True,
                gridcolor="#334155",
                tickformat="%Y-%m-%d %H:%M",
                tickangle=45
            )
            fig.update_layout(
                paper_bgcolor="#0f172a",
                plot_bgcolor="#0f172a",
                font_color="white",
                height=300,
                margin=dict(l=10, r=10, t=40, b=50),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.add_annotation(
                text=f"Total High: {len(high_df)}",
                xref="paper", yref="paper",
                x=0.02, y=0.95,
                showarrow=False,
                font=dict(color="#ef4444", size=12),
                bgcolor="rgba(15,23,42,0.7)",
                bordercolor="#334155",
                borderwidth=1,
                borderpad=4,
                opacity=0.9
            )
            return fig

        except Exception as e:
            print(f"Timeline error: {e}")
            return blank.update_layout(title=f"Error: {str(e)[:80]}")

    # ── Events table & feature importance ──
    @app.callback(
        Output("events-table", "data"),
        Output("events-table", "columns"),
        Output("feature-importance-chart", "figure"),
        Input("refresh-btn", "n_clicks"),
        Input("load-trigger", "data"),
        Input("auto-refresh", "n_intervals"),
        Input("priority-filter", "value"),
        Input("hour-filter", "value"),
        State("token-store", "data"),
        prevent_initial_call=False
    )
    def update_table(_clicks, _trigger, _interval, priority_filter, hour_range, token_data):
        if not token_data or not token_data.get("token"):
            return [], [], empty_fig()

        headers = {"Authorization": f"Bearer {token_data['token']}"}
        try:
            events_resp = requests.get(f"{API}/prioritized", headers=headers, timeout=30)
            imp_resp = requests.get(f"{API}/feature-importance", headers=headers, timeout=10)
            if events_resp.status_code != 200:
                return [], [], empty_fig()

            df = pd.DataFrame(events_resp.json())
            if df.empty:
                return [], [], empty_fig()

            if priority_filter and priority_filter != "All" and "priority" in df.columns:
                df = df[df["priority"] == priority_filter]
            if "hour" in df.columns and hour_range:
                df = df[(df["hour"] >= hour_range[0]) & (df["hour"] <= hour_range[1])]
            if "risk_score" in df.columns:
                df["risk_score"] = df["risk_score"].round(4)

            if "status" not in df.columns:
                df["status"] = "unassigned"
            if "assigned_to" not in df.columns:
                df["assigned_to"] = ""

            display_cols = ["event_id", "hour", "day_of_week", "risk_score", "priority", "status", "assigned_to"]
            display_cols = [c for c in display_cols if c in df.columns]
            columns = [
                {"name": c.replace("_", " ").title(), "id": c, "editable": c in ["status", "assigned_to"]}
                for c in display_cols
            ]
            data = df[display_cols].to_dict(orient="records")

            # ── Feature Importance chart ──
            bar = empty_fig()
            if imp_resp.status_code == 200:
                imp = imp_resp.json()
                print("Feature importance response:", imp)

                if imp and any(imp.values()):
                    imp_df = pd.DataFrame(list(imp.items()), columns=["Feature", "Importance"])
                    imp_df = imp_df.sort_values("Importance", ascending=True)
                    bar = px.bar(
                        imp_df,
                        x="Importance",
                        y="Feature",
                        orientation="h",
                        color="Importance",
                        color_continuous_scale="Blues",
                        title="Feature Importances"
                    ).update_layout(
                        paper_bgcolor="#0f172a",
                        plot_bgcolor="#0f172a",
                        font_color="white",
                        height=300,
                        margin=dict(l=10, r=10, t=40, b=10),
                        xaxis=dict(title="Importance", gridcolor="#334155"),
                        yaxis=dict(title="", gridcolor="#334155")
                    )
                else:
                    bar = go.Figure()
                    bar.add_annotation(
                        text="No feature importance data available",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(color="white", size=14)
                    )
                    bar.update_layout(
                        paper_bgcolor="#0f172a",
                        plot_bgcolor="#0f172a",
                        font_color="white",
                        height=300,
                        margin=dict(l=10, r=10, t=30, b=10)
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
        State("token-store", "data"),
        prevent_initial_call=True
    )
    def update_shap(n_clicks, event_index, token_data):
        if not token_data or not token_data.get("token"):
            return empty_fig(), dbc.Alert("🔐 Not authenticated — please log in again", color="danger")

        if event_index is None or event_index == "":
            return empty_fig(), dbc.Alert("Enter an event index — click a stat card to see available indices", color="warning")

        try:
            event_index = int(event_index)
        except (ValueError, TypeError):
            return empty_fig(), dbc.Alert("Index must be a whole number", color="warning")

        headers = {"Authorization": f"Bearer {token_data['token']}"}
        try:
            # Check valid range
            range_resp = requests.get(f"{API}/shap/available-indices", headers=headers, timeout=10)
            if range_resp.status_code == 401:
                return empty_fig(), dbc.Alert("🔐 Session expired — please log out and log in again", color="danger")
            if range_resp.status_code == 200:
                info = range_resp.json()
                max_idx = info.get("max", 9999)
                if event_index < 0 or event_index > max_idx:
                    return empty_fig(), dbc.Alert(
                        f"❌ Index {event_index} is out of range. Valid indices: 0 – {max_idx}. "
                        f"Click a stat card to see events and their indices.",
                        color="danger"
                    )

            resp = requests.get(f"{API}/shap/event/{event_index}", headers=headers, timeout=60)
            if resp.status_code == 401:
                return empty_fig(), dbc.Alert("🔐 Session expired — please log out and log in again", color="danger")
            if resp.status_code == 404:
                return empty_fig(), dbc.Alert(f"❌ Event index {event_index} not found. Use the stat cards above to find valid indices.", color="warning")
            if resp.status_code != 200:
                return empty_fig(), dbc.Alert(f"API error {resp.status_code}: {resp.text[:120]}", color="danger")

            d = resp.json()
            features = d.get("feature_names", [])
            shap_vals = d.get("shap_values", [])
            feature_vals = d.get("feature_values", [])
            interp = d.get("interpretation", "")
            pred_label = d.get("predicted_label", "Unknown")

            if not features:
                return empty_fig(), dbc.Alert("No SHAP data returned for this event", color="warning")

            paired = sorted(zip(features, shap_vals, feature_vals), key=lambda x: abs(x[1]), reverse=True)[:10]
            f_top, s_top, v_top = zip(*paired)

            fig = go.Figure(go.Bar(
                x=list(s_top),
                y=[f"{f} = {round(v, 2)}" for f, v in zip(f_top, v_top)],
                orientation="h",
                marker_color=["#ef4444" if v > 0 else "#10b981" for v in s_top],
                text=[f"{v:.3f}" for v in s_top],
                textposition="outside"
            ))
            fig.update_layout(
                title=f"Event #{event_index} → {pred_label}",
                xaxis_title="SHAP Value (🔴 increases risk | 🟢 reduces risk)",
                paper_bgcolor="#0f172a",
                plot_bgcolor="#0f172a",
                font_color="white",
                height=320,
                margin=dict(l=160, r=40, t=50, b=20)
            )

            interpretation = dbc.Alert([
                html.B(f"📌 Event #{event_index} — "),
                html.Span(pred_label, style={"color": "#60a5fa", "fontWeight": "700"}),
                html.Br(),
                html.Span(interp, style={"fontSize": "13px"})
            ], color="info")

            return fig, interpretation

        except requests.exceptions.ConnectionError:
            return empty_fig(), dbc.Alert("🔌 Cannot connect to backend — is it running?", color="danger")
        except Exception as e:
            print(f"SHAP error: {e}")
            return empty_fig(), dbc.Alert(f"Unexpected error: {str(e)[:100]}", color="danger")

    # ── Feedback submission ──
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
    def submit_feedback(n_clicks, event_index, correct_label, correct_flag, comment, token_data):
        if not token_data or not token_data.get("token"):
            return dbc.Alert("🔐 Not authenticated — please log in again", color="warning")
        if event_index is None:
            return dbc.Alert("Enter an event index first — get it from the stat cards", color="warning")
        if not correct_label:
            return dbc.Alert("Select the correct label", color="warning")

        headers = {"Authorization": f"Bearer {token_data['token']}"}
        try:
            cls_resp = requests.get(f"{API}/classification/event/{event_index}", headers=headers, timeout=10)
            if cls_resp.status_code == 401:
                return dbc.Alert("🔐 Session expired — please log out and log in again", color="danger")
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
                return dbc.Alert(f"✅ Feedback submitted for event #{event_index}! ID: {fb_resp.json().get('feedback_id')}", color="success")
            return dbc.Alert(f"❌ Failed: {fb_resp.json().get('detail', 'Unknown error')}", color="danger")

        except requests.exceptions.ConnectionError:
            return dbc.Alert("🔌 Cannot connect to backend.", color="danger")
        except Exception as e:
            print(f"Feedback error: {e}")
            return dbc.Alert(f"❌ Error: {str(e)[:100]}", color="danger")

    # ── Feedback History Modal ──
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

        headers = {"Authorization": f"Bearer {token_data['token']}"}
        try:
            resp = requests.get(f"{API}/classification/feedback/all", headers=headers, timeout=10)
            if resp.status_code == 403:
                return [], [], "⛔ Access Denied", {"display": "block"}
            if resp.status_code == 401:
                return [], [], "🔐 Session expired", {"display": "block"}
            if resp.status_code != 200:
                return [], [], f"❌ Error {resp.status_code}", {"display": "block"}

            rows = resp.json()
            if not rows:
                return [], [], "No feedback submitted yet", {"display": "none"}

            df = pd.DataFrame(rows)
            role = token_data.get("role", "")

            # Admin sees more columns, but we remove 'status' from both
            if role in ["system_admin", "admin"]:
                cols = ["id", "event_index", "predicted_label", "correct_label",
                        "is_correctly_classified", "analyst_username", "submitted_at", "reviewed_by"]
            else:
                cols = ["id", "event_index", "predicted_label", "correct_label",
                        "is_correctly_classified", "submitted_at"]

            cols = [c for c in cols if c in df.columns]
            columns = [{"name": c.replace("_", " ").title(), "id": c} for c in cols]
            data = df[cols].to_dict(orient="records")

            return data, columns, f"📊 Feedback History ({len(data)} entries)", {"display": "none"}

        except Exception as e:
            print(f"Feedback modal error: {e}")
            return [], [], f"Error: {str(e)[:100]}", {"display": "block"}





    # ── Events modal ──
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

        if triggered_id not in ["high-stat-card", "medium-stat-card", "low-stat-card", "total-stat-card"]:
            return is_open, "Events", [], [], {"display": "block"}

        priority_map = {
            "high-stat-card": "High",
            "medium-stat-card": "Medium",
            "low-stat-card": "Low",
            "total-stat-card": "All",
        }
        selected_priority = priority_map[triggered_id]

        if not token_data or not token_data.get("token"):
            return True, "🔐 Auth Token Missing — please log in again", [], [], {"display": "block"}

        headers = {"Authorization": f"Bearer {token_data['token']}"}
        try:
            resp = requests.get(f"{API}/prioritized", headers=headers, timeout=15)
            if resp.status_code == 401:
                return True, "🔐 Session expired — please log in again", [], [], {"display": "block"}
            if resp.status_code != 200:
                return True, f"❌ System Error {resp.status_code}", [], [], {"display": "block"}

            df = pd.DataFrame(resp.json())

            if "index" not in df.columns:
                df.insert(0, "index", df.index)

            if not df.empty and selected_priority != "All":
                df = df[df["priority"] == selected_priority]

            display_cols = ["id", "event_id", "hour", "day_of_week", "risk_score", "priority"]
            display_cols = [c for c in display_cols if c in df.columns]

            columns = [
                {
                    "name": "ID" if c == "id" else c.replace("_", " ").title(),
                    "id": c,
                    "editable": False
                }
                for c in display_cols
            ]
            data = df[display_cols].to_dict(orient="records")

            icon = {"High": "🔥", "Medium": "⚠️", "Low": "✅", "All": "📊"}.get(selected_priority, "📊")
            title = f"{icon} {selected_priority} Priority — {len(df)} events"

            return True, title, data, columns, {"display": "none"}

        except Exception as e:
            print(f"Modal Fetch Exception: {e}")
            return True, "🔌 Service Connection Interrupted", [], [], {"display": "block"}

    # ── Events table — cell edit (status / assigned_to) ──
    @app.callback(
        Output("events-table", "data", allow_duplicate=True),
        Input("events-table", "cell_edited"),
        State("events-table", "data"),
        State("token-store", "data"),
        prevent_initial_call=True
    )
    def handle_cell_edit(cell_edited, current_rows, token_data):
        if not token_data or not token_data.get("token"):
            return current_rows
        if not cell_edited or not current_rows:
            return current_rows

        row_id = cell_edited.get("row_id")
        col_id = cell_edited.get("column_id")
        new_value = cell_edited.get("value")

        if col_id not in ["status", "assigned_to"] or row_id is None or row_id >= len(current_rows):
            return current_rows

        event_id = current_rows[row_id].get("event_id")
        if not event_id:
            return current_rows

        headers = {"Authorization": f"Bearer {token_data['token']}"}
        current_status = current_rows[row_id].get("status", "unassigned")
        current_assigned = current_rows[row_id].get("assigned_to", "")

        payload = {
            "status": new_value if col_id == "status" else current_status,
            "assigned_to": new_value if col_id == "assigned_to" else current_assigned
        }

        try:
            resp = requests.post(f"{API}/events/{event_id}/status", json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                current_rows[row_id][col_id] = new_value
            else:
                print(f"Failed to update: {resp.status_code} — {resp.text}")
        except Exception as e:
            print(f"Cell edit error: {e}")

        return current_rows

    # ── Populate mini tables in priority cards ──
    @app.callback(
        Output("high-events-table", "data"),
        Output("medium-events-table", "data"),
        Output("low-events-table", "data"),
        Input("refresh-btn", "n_clicks"),
        Input("load-trigger", "data"),
        Input("auto-refresh", "n_intervals"),
        State("token-store", "data"),
        prevent_initial_call=False
    )
    def update_mini_tables(_clicks, _trigger, _interval, token_data):
        if not token_data or not token_data.get("token"):
            return [], [], []

        headers = {"Authorization": f"Bearer {token_data['token']}"}
        try:
            resp = requests.get(f"{API}/prioritized", headers=headers, timeout=30)
            if resp.status_code != 200:
                return [], [], []

            df = pd.DataFrame(resp.json())
            if df.empty:
                return [], [], []

            if "id" not in df.columns:
                df.insert(0, "id", df.index)
            if "risk_score" not in df.columns:
                df["risk_score"] = 0.0
            if "event_id" not in df.columns:
                df["event_id"] = "N/A"

            cols = ["id", "event_id", "risk_score", "priority"]
            df = df[[c for c in cols if c in df.columns]]

            high_df = df[df["priority"] == "High"].sort_values("risk_score", ascending=False).head(5)
            med_df = df[df["priority"] == "Medium"].sort_values("risk_score", ascending=False).head(5)
            low_df = df[df["priority"] == "Low"].sort_values("risk_score", ascending=False).head(5)

            def format_rows(dataframe):
                rows = dataframe.to_dict(orient="records")
                for row in rows:
                    row["action"] = "🔍 Explain"
                return rows

            return format_rows(high_df), format_rows(med_df), format_rows(low_df)

        except Exception as e:
            print(f"update_mini_tables error: {e}")
            return [], [], []

    # ── Handle clicks on "Explain" in mini tables ──
    @app.callback(
        Output("shap-index", "value", allow_duplicate=True),
        Output("shap-btn", "n_clicks", allow_duplicate=True),
        Output("high-events-table", "data", allow_duplicate=True),
        Output("medium-events-table", "data", allow_duplicate=True),
        Output("low-events-table", "data", allow_duplicate=True),
        Input("high-events-table", "cell_clicked"),
        Input("medium-events-table", "cell_clicked"),
        Input("low-events-table", "cell_clicked"),
        State("high-events-table", "data"),
        State("medium-events-table", "data"),
        State("low-events-table", "data"),
        State("token-store", "data"),
        prevent_initial_call=True
    )
    def on_mini_table_click(high_click, med_click, low_click, high_data, med_data, low_data, token_data):
        triggered_id = ctx.triggered_id
        if triggered_id == "high-events-table":
            cell_click = high_click
            table_data = high_data
        elif triggered_id == "medium-events-table":
            cell_click = med_click
            table_data = med_data
        elif triggered_id == "low-events-table":
            cell_click = low_click
            table_data = low_data
        else:
            raise PreventUpdate

        if cell_click is None:
            raise PreventUpdate

        row = cell_click["row"]
        col = cell_click["column_id"]
        row_data = table_data[row]

        # Only Explain button
        if col == "action":
            index_val = row_data.get("id")
            if index_val is not None:
                return index_val, 1, high_data, med_data, low_data
            else:
                raise PreventUpdate

        raise PreventUpdate