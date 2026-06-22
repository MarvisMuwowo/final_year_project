# components.py
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc

def stat_card(icon, color, label, count_id, card_id):
    """Clickable stat card that triggers a modal."""
    return html.Div([
        html.Div(
            id=card_id,
            n_clicks=0,
            style={"cursor": "pointer", "transition": "transform 0.1s ease"},
            children=[
                html.Div(icon, style={"fontSize": "32px", "color": color, "marginBottom": "8px"}),
                html.H6(label, style={"color": "#cbd5e1", "fontSize": "12px", "margin": "0",
                                      "textTransform": "uppercase", "letterSpacing": "0.5px"}),
                html.H2(id=count_id, style={"fontSize": "2rem", "fontWeight": "700",
                                            "color": color, "margin": "0", "lineHeight": "1.2"})
            ]
        )
    ], className="text-center p-3 rounded-3 shadow-sm",
       style={"backgroundColor": "#1e293b", "borderLeft": f"4px solid {color}"})

def chart_card(title, graph_id):
    return dbc.Card([
        dbc.CardHeader(html.H6(title, className="mb-0",
                               style={"color": "#3b82f6", "fontWeight": "600"})),
        dbc.CardBody(dcc.Graph(id=graph_id, config={"displayModeBar": False}))
    ], className="shadow-sm",
       style={"backgroundColor": "#1e293b", "border": "none", "height": "100%"})

def events_modal():
    """Modal for showing events by priority (clickable stat cards)."""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="events-modal-title", children="Events")),
        dbc.ModalBody([
            html.Div(id="modal-loading", children="Loading events...", style={"color": "#94a3b8"}),
            dash_table.DataTable(
                id="events-modal-table",
                page_size=15,
                style_table={"overflowX": "auto", "minHeight": "300px"},
                style_header={"backgroundColor": "#0f172a", "color": "#3b82f6",
                              "fontWeight": "600", "fontSize": "12px", "border": "none", "padding": "8px"},
                style_data={"backgroundColor": "#1e293b", "color": "#e2e8f0",
                            "fontSize": "12px", "border": "none", "padding": "6px"},
                style_data_conditional=[
                    {"if": {"filter_query": '{priority} = "High"'}, "backgroundColor": "#7f1a1a", "color": "#fca5a5"},
                    {"if": {"filter_query": '{priority} = "Medium"'}, "backgroundColor": "#78350f", "color": "#fcd34d"},
                    {"if": {"filter_query": '{priority} = "Low"'}, "backgroundColor": "#064e3b", "color": "#6ee7b7"},
                ],
            )
        ]),
        dbc.ModalFooter(dbc.Button("Close", id="close-events-modal", className="ml-auto")),
    ], id="events-modal", size="xl", is_open=False, scrollable=True)

def feedback_history_modal():
    """Modal for showing feedback history (accessible to both Analysts and Admins)."""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="feedback-modal-title", children="Feedback History")),
        dbc.ModalBody([
            html.Div(id="feedback-modal-loading", children="Loading feedback...", style={"color": "#94a3b8"}),
            dash_table.DataTable(
                id="feedback-modal-table",
                page_size=10,
                style_table={"overflowX": "auto", "minHeight": "250px"},
                style_header={"backgroundColor": "#0f172a", "color": "#3b82f6",
                              "fontWeight": "600", "fontSize": "12px", "border": "none", "padding": "8px"},
                style_data={"backgroundColor": "#1e293b", "color": "#e2e8f0",
                            "fontSize": "12px", "border": "none", "padding": "6px"},
                style_data_conditional=[
                    {"if": {"filter_query": '{is_correctly_classified} = false'},
                     "backgroundColor": "#7f1a1a", "color": "#fca5a5"},
                    {"if": {"filter_query": '{is_correctly_classified} = true'},
                     "backgroundColor": "#064e3b", "color": "#6ee7b7"},
                    {"if": {"filter_query": '{status} = "pending"'},
                     "color": "#fcd34d"},
                    {"if": {"filter_query": '{status} = "reviewed"'},
                     "color": "#6ee7b7"},
                ],
            )
        ]),
        dbc.ModalFooter(dbc.Button("Close", id="close-feedback-modal", className="ml-auto")),
    ], id="feedback-history-modal", size="xl", is_open=False, scrollable=True)