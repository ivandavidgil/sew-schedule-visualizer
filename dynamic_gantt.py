import base64
import io
import pandas as pd
from datetime import timedelta

import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px

# Create the Dash app
app = dash.Dash(__name__)
server = app.server

# App layout with upload component, control dropdowns, and one dynamic graph.
app.layout = html.Div([
    html.H2("Dynamic Sewing Production Schedule Visualizer"),
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drag and Drop or ', html.A('Select CSV File')]),
        style={
            'width': '98%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),
    # Upload status message
    html.Div(id="upload-status", children="No file uploaded yet", 
             style={'textAlign': 'center', 'color': 'blue', 'margin': '10px'}),
    # Store the parsed CSV data
    dcc.Store(id="stored-data"),
    
    # Control panel for dynamic visualization
    html.Div([
        html.Div([
            html.Label("View by:"),
            dcc.Dropdown(
                id="view-by-dropdown",
                options=[
                    {"label": "Machine Name", "value": "Machine Name"},
                    {"label": "Sew Type", "value": "Sew Type"},
                    {"label": "Sewer Name", "value": "Sewer Name"}
                ],
                value="Sewer Name"
            )
        ], style={'width': '30%', 'display': 'inline-block', 'margin': '10px'}),
        html.Div([
            html.Label("Color by:"),
            dcc.Dropdown(
                id="color-by-dropdown",
                options=[
                    {"label": "Machine Name", "value": "Machine Name"},
                    {"label": "Sew Type", "value": "Sew Type"},
                    {"label": "Sewer Name", "value": "Sewer Name"}
                ],
                value="Sew Type"
            )
        ], style={'width': '30%', 'display': 'inline-block', 'margin': '10px'})
    ]),
    html.Div([
        html.Div([
            html.Label("Machine Name Filter:"),
            dcc.Dropdown(id="machine-filter-dropdown")
        ], style={'width': '30%', 'display': 'inline-block', 'margin': '10px'}),
        html.Div([
            html.Label("Sew Type Filter:"),
            dcc.Dropdown(id="sewtype-filter-dropdown")
        ], style={'width': '30%', 'display': 'inline-block', 'margin': '10px'}),
        html.Div([
            html.Label("Sewer Name Filter:"),
            dcc.Dropdown(id="sewer-filter-dropdown")
        ], style={'width': '30%', 'display': 'inline-block', 'margin': '10px'})
    ]),
    dcc.Graph(id="dynamic-graph")
])

def convert_timedelta_in_fig(fig):
    """
    Convert any timedelta objects in each trace's x-values to milliseconds
    to ensure the figure is JSON serializable.
    """
    for trace in fig.data:
        if hasattr(trace, 'x'):
            new_x = []
            for val in trace.x:
                if isinstance(val, (pd.Timedelta, timedelta)):
                    new_x.append(val.total_seconds() * 1000)
                else:
                    new_x.append(val)
            trace.x = new_x
    return fig

# Callback to parse the uploaded CSV and store it; also update upload status.
@app.callback(
    [Output("stored-data", "data"),
     Output("upload-status", "children")],
    [Input("upload-data", "contents")],
    [State("upload-data", "filename")]
)
def parse_upload(contents, filename):
    if contents is None:
        return None, "No file uploaded yet."
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
    except Exception as e:
        return None, f"Error reading CSV: {e}"
    
    # Validate required columns; if "Machine Name" is missing, add it with default "Unknown".
    required_columns = ["Sewer Name", "Start Time", "Operation Time", "Sew Type"]
    for col in required_columns:
        if col not in df.columns:
            return None, f"Missing required column: {col}"
    if "Machine Name" not in df.columns:
        df["Machine Name"] = "Unknown"
    
    # Data processing: strip extra spaces, convert Start Time to datetime, compute End Time.
    df["Sewer Name"] = df["Sewer Name"].astype(str).str.strip()
    try:
        df["Start Time"] = pd.to_datetime(df["Start Time"], format="%Y-%m-%d %H:%M")
    except Exception as e:
        return None, f"Error parsing Start Time: {e}"
    df["End Time"] = df["Start Time"] + pd.to_timedelta(df["Operation Time"], unit="m")
    
    return df.to_json(date_format="iso", orient="split"), f"File successfully uploaded: {filename}"

# Callback to populate the three filter dropdowns based on the loaded data.
@app.callback(
    [Output("machine-filter-dropdown", "options"),
     Output("machine-filter-dropdown", "value"),
     Output("sewtype-filter-dropdown", "options"),
     Output("sewtype-filter-dropdown", "value"),
     Output("sewer-filter-dropdown", "options"),
     Output("sewer-filter-dropdown", "value")],
    Input("stored-data", "data")
)
def update_filter_options(data):
    if data is None:
        return [], None, [], None, [], None
    df = pd.read_json(data, orient="split")
    machine_options = [{"label": "ALL", "value": "ALL"}] + [
        {"label": m, "value": m} for m in sorted(df["Machine Name"].unique())
    ]
    sewtype_options = [{"label": "ALL", "value": "ALL"}] + [
        {"label": s, "value": s} for s in sorted(df["Sew Type"].unique())
    ]
    sewer_options = [{"label": "ALL", "value": "ALL"}] + [
        {"label": s, "value": s} for s in sorted(df["Sewer Name"].unique())
    ]
    return machine_options, "ALL", sewtype_options, "ALL", sewer_options, "ALL"

# Callback to generate the dynamic timeline chart based on control selections.
@app.callback(
    Output("dynamic-graph", "figure"),
    [Input("stored-data", "data"),
     Input("view-by-dropdown", "value"),
     Input("color-by-dropdown", "value"),
     Input("machine-filter-dropdown", "value"),
     Input("sewtype-filter-dropdown", "value"),
     Input("sewer-filter-dropdown", "value")]
)
def update_dynamic_graph(data, view_by, color_by, machine_filter, sewtype_filter, sewer_filter):
    if data is None:
        return {}
    try:
        # Read the full data from storage
        full_df = pd.read_json(data, orient="split")
        # Start with the full dataset for filtering
        df = full_df.copy()
        
        # Apply filters if not set to "ALL"
        if machine_filter and machine_filter != "ALL":
            df = df[df["Machine Name"] == machine_filter]
        if sewtype_filter and sewtype_filter != "ALL":
            df = df[df["Sew Type"] == sewtype_filter]
        if sewer_filter and sewer_filter != "ALL":
            df = df[df["Sewer Name"] == sewer_filter]
        
        if df.empty:
            return {"data": [], "layout": {"title": "No data matches the selected filters."}}
        
        # Build timeline chart using the selected view (y-axis) and color attributes.
        fig = px.timeline(
            df,
            x_start="Start Time",
            x_end="End Time",
            y=view_by,
            color=color_by,
            hover_data=["Machine Name", "Sew Type", "Sewer Name", "Operation Time"]
        )
        
        # If no filter is applied at all, use the full dataset's categories;
        # otherwise, use only the categories from the filtered dataset.
        if machine_filter == "ALL" and sewtype_filter == "ALL" and sewer_filter == "ALL":
            categories = sorted(full_df[view_by].unique())
        else:
            categories = sorted(df[view_by].unique())
        
        # Update y-axis to include only the categories present in the filtered data.
        fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=categories)
        
        # Dynamically calculate chart height: 40 pixels per category, minimum 600 pixels.
        chart_height = max(600, 40 * len(categories))
        fig.update_layout(
            title="Schedule Visualization",
            xaxis_title="Time",
            yaxis_title=view_by,
            margin=dict(l=40, r=40, t=40, b=40),
            height=chart_height
        )
        fig = convert_timedelta_in_fig(fig)
        return fig
    except Exception as e:
        return {"data": [], "layout": {"title": f"Error generating chart: {e}"}}


if __name__ == '__main__':
    app.run_server(debug=True)
