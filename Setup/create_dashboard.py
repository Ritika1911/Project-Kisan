import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
from google.cloud import bigquery

# Sample data
data = []

query = """
    SELECT *
    FROM `tonal-land-467116-p9.Real_Time_Price_Details.market_data`
"""
client = bigquery.Client()
# Run the query
df = client.query(query).to_dataframe()
print(df)

df['Min_Price'] = pd.to_numeric(df['Min_Price'])
df['Max_Price'] = pd.to_numeric(df['Max_Price'])
df['Modal_Price'] = pd.to_numeric(df['Modal_Price'])
df['Arrival_Date'] = pd.to_datetime(df['Arrival_Date'], dayfirst=True)

# Create melted DataFrame for box/violin plots
df_melted = df.melt(
    id_vars=['Commodity', 'Arrival_Date'],
    value_vars=['Min_Price', 'Modal_Price', 'Max_Price'],
    var_name='Price_Type',
    value_name='Price'
)

# Initialize app
app = dash.Dash(__name__)
app.title = "Price Distribution Dashboard"

# Layout
app.layout = html.Div([
    html.H2("Karnataka Agricultural Market Dashboard",style={"textAlign": "center"}),
    
    html.Div([
        html.Div([
            html.Label("District"),
            dcc.Dropdown(
                id='district-dropdown',
                options=[{"label": d, "value": d} for d in sorted(df["District"].unique())],
                value=sorted(df["District"].unique())[0]
            )
        ], style={'width': '30%', 'display': 'inline-block'}),

        html.Div([
            html.Label("Market"),
            dcc.Dropdown(id='market-dropdown')
        ], style={'width': '30%', 'display': 'inline-block', 'paddingLeft': '4%'}),

        html.Div([
            html.Label("Commodity"),
            dcc.Dropdown(id='commodity-dropdown')
        ], style={'width': '30%', 'display': 'inline-block', 'paddingLeft': '4%'}),
    ], style={'paddingBottom': '20px'}),
    
    html.Div([
        html.Div([dcc.Graph(id="min-line")], style={'width': '33%', 'display': 'inline-block'}),
        html.Div([dcc.Graph(id="max-line")], style={'width': '33%', 'display': 'inline-block'}),
        html.Div([dcc.Graph(id="modal-line")], style={'width': '33%', 'display': 'inline-block'}),
    ]),

    html.H3("Modal Price by Market (Filtered by Commodity & Arrival Date)", style={"textAlign": "center"}),

    html.Div([
        html.Div([
            html.Label("Select Commodity"),
            dcc.Dropdown(
                id='commodity-dropdown1',
                options=[{"label": c, "value": c} for c in sorted(df["Commodity"].unique())],
                value=sorted(df["Commodity"].unique())[0]
            ),
        ], style={'width': '48%', 'display': 'inline-block'}),

        html.Div([
            html.Label("Select Arrival Date"),
            dcc.Dropdown(id='date-dropdown')
        ], style={'width': '48%', 'display': 'inline-block', 'paddingLeft': '10px'}),
    ], style={"marginBottom": "30px"}),

    dcc.Graph(id="modal-price-bar")

])

@app.callback(
    Output('date-dropdown', 'options'),
    Output('date-dropdown', 'value'),
    Input('commodity-dropdown1', 'value')
)
def update_dates(commodity):
    filtered = df[df["Commodity"] == commodity]
    dates = sorted(filtered["Arrival_Date"].dt.strftime('%Y-%m-%d').unique())
    options = [{"label": d, "value": d} for d in dates]
    return options, dates[0] if dates else None

# Update bar chart
@app.callback(
    Output("modal-price-bar", "figure"),
    Input("commodity-dropdown1", "value"),
    Input("date-dropdown", "value")
)
def update_graph(commodity, date_str):
    if not date_str:
        return px.bar(title="No data available")

    date = pd.to_datetime(date_str)
    filtered_df = df[(df["Commodity"] == commodity) & (df["Arrival_Date"] == date)]

    fig = px.bar(
        filtered_df,
        x="Market",
        y="Modal_Price",
        color="Market",
        text="Modal_Price",
        title=f"Modal Price of {commodity} on {date_str}"
    )

    fig.update_layout(
        yaxis_title="Modal Price",
        xaxis_title="Market",
        height=450
    )

    return fig

@app.callback(
    Output('market-dropdown', 'options'),
    Output('market-dropdown', 'value'),
    Input('district-dropdown', 'value')
)
def update_market_options(selected_district):
    markets = df[df['District'] == selected_district]['Market'].unique()
    options = [{"label": m, "value": m} for m in sorted(markets)]
    return options, options[0]["value"] if options else None

@app.callback(
    Output('commodity-dropdown', 'options'),
    Output('commodity-dropdown', 'value'),
    Input('market-dropdown', 'value'),
    Input('district-dropdown', 'value')
)
def update_commodity_options(selected_market, selected_district):
    subset = df[(df["District"] == selected_district) & (df["Market"] == selected_market)]
    commodities = subset["Commodity"].unique()
    options = [{"label": c, "value": c} for c in sorted(commodities)]
    return options, options[0]["value"] if options else None

@app.callback(
    Output("min-line", "figure"),
    Output("max-line", "figure"),
    Output("modal-line", "figure"),
    Input("district-dropdown", "value"),
    Input("market-dropdown", "value"),
    Input("commodity-dropdown", "value")
)
def update_graphs(selected_district, selected_market, selected_commodity):
    filtered = df[
        (df["District"] == selected_district) &
        (df["Market"] == selected_market) &
        (df["Commodity"] == selected_commodity)
    ]

    min_fig = px.line(filtered, x="Arrival_Date", y="Min_Price", markers=True, title="Min Price")
    max_fig = px.line(filtered, x="Arrival_Date", y="Max_Price", markers=True, title="Max Price")
    modal_fig = px.line(filtered, x="Arrival_Date", y="Modal_Price", markers=True, title="Modal Price")

    for fig in [min_fig, max_fig, modal_fig]:
        fig.update_layout(margin=dict(t=40, l=30, r=10, b=30), height=400, hovermode="x unified")

    return min_fig, max_fig, modal_fig

# Run server
if __name__ == '__main__':
    app.run(debug=True)