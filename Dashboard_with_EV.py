from flask import Flask
from dash import Dash, dcc, html, dash_table
from dash.dependencies import Input, Output
import mysql.connector
import pandas as pd
import json
import pytz
from datetime import datetime
import dash_bootstrap_components as dbc

# Flask setup
server = Flask(__name__)

# Dash setup
app = Dash(__name__, server=server, url_base_pathname='/', title="GNIRE-GLEAMM EMS Testing")

# Layout with navigation links
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# Database connection setup
def get_db_connection():
    connection = mysql.connector.connect(
        host='192.168.10.52',
        user='SANKA',
        password='3Sssmalaka@!',
        database='GLEAMM_NIRE'
    )
    return connection

# Function to fetch data from the last 20 minutes
def fetch_data_last_20_minutes():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        query = """
        SELECT ts, value_string FROM data 
        WHERE topic_id = 5 
        AND ts >= NOW() - INTERVAL 1 HOUR
        ORDER BY ts DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        data_list = []
        for row in rows:
            ts, value_string = row
            data = json.loads(value_string)
            data_list.append((ts, data))

        return data_list

    finally:
        cursor.close()
        connection.close()

# Helper function to convert timestamps based on selected timezone
def convert_timestamps(data_list, timezone):
    if timezone == 'Local':
        local_tz = pytz.timezone('America/New_York')  # Change this to your local timezone
        data_list = [(ts.astimezone(local_tz) if isinstance(ts, datetime) else ts, data) for ts, data in data_list]
    return data_list

# Helper function to guess missing threshold values
def guess_missing_thresholds(thresholds_list):
    last_thresholds = None
    for i, thresholds in enumerate(thresholds_list):
        if thresholds is None:
            if last_thresholds is not None:
                thresholds_list[i] = last_thresholds
        else:
            last_thresholds = thresholds
    return thresholds_list

def guess_missing_thresholds_spit(control_commands):
    priority_thresholds = {}
    total_thresholds = []
    last_priority_thresholds = None
    last_total_threshold = None
    
    for command in control_commands:
        if isinstance(command, dict):
            current_priority_thresholds = {priority: cmd[1] for priority, cmd in command.items()}
            last_priority_thresholds = current_priority_thresholds
            total_thresholds.append(sum(cmd[1] for cmd in command.values()))
        elif isinstance(command, list) and len(command) == 2:
            last_total_threshold = command[1]
            current_priority_thresholds = None
            total_thresholds.append(last_total_threshold)
        else:
            current_priority_thresholds = last_priority_thresholds
            total_thresholds.append(last_total_threshold)

        # Update the priority thresholds dictionary
        if current_priority_thresholds:
            for priority, threshold in current_priority_thresholds.items():
                if priority not in priority_thresholds:
                    priority_thresholds[priority] = []
                priority_thresholds[priority].append(threshold)
        else:
            for priority in priority_thresholds:
                priority_thresholds[priority].append(None)

    # Insert the latest thresholds at the end of the lists
    if last_priority_thresholds:
        for priority, threshold in last_priority_thresholds.items():
            if priority in priority_thresholds:
                priority_thresholds[priority][-1] = threshold
            else:
                priority_thresholds[priority] = [threshold]
    
    if last_total_threshold is not None:
        total_thresholds[-1] = last_total_threshold
    for priority in priority_thresholds:
        priority_thresholds[priority].reverse()
    total_thresholds.reverse()
    return priority_thresholds, total_thresholds

# Home Page layout
home_layout = html.Div([
    html.H1("Home Page"),
    dcc.Link('Go to Device Page', href='/device-page'),
    dcc.Interval(
        id='interval-component-home',
        interval=40*1000,  # Update every 40 seconds
        n_intervals=0
    ),
    # EV Card at the top of the Home Page
    dbc.Card(
        dbc.CardBody([
            html.Img(src='/assets/ev_image.png', style={'width': '100px', 'height': '100px'}),  # Replace with your image path
            html.H4("EV Power Consumption", className="card-title"),
            html.Div(id='ev-power-display-home', style={'fontSize': 20, 'margin': '10px 0'}),
            html.Div(id='ev-status-light-home', style={'width': '20px', 'height': '20px', 'borderRadius': '50%'})  # Circle for status light
        ]),
        style={'width': '18rem', 'margin': '20px'}
    ),
    dcc.Dropdown(
        id='timezone-selector-home',
        options=[
            {'label': 'UTC', 'value': 'UTC'},
            {'label': 'Local Time', 'value': 'Local'},
        ],
        value='UTC',  # Default value
        style={'width': '50%', 'margin-bottom': '20px'}
    ),
    html.Div(id='control-command-display-home', style={'fontSize': 24, 'margin': '20px 0'}),
    dcc.Graph(id='total-consumption-line-graph-home'),
    dcc.Graph(id='priority-trend-line-graph-home'),
])

# Define status colors
status_colors = {
    0: '#00e118',  # Off
    1: '#3165f8',  # On
    8: '#c7cd00',  # Standby
    11: '#fd5d5d',  # Communication Error
    12:"green",
    13:"gold",
    14:"red"
}

# Device Page layout
device_layout = html.Div([
    html.H1("Device Page"),
    dcc.Link('Go to Home Page', href='/'),
    dcc.Interval(
        id='interval-component-device',
        interval=40*1000,  # Update every 40 seconds
        n_intervals=0
    ),
    dcc.Dropdown(
        id='timezone-selector-device',
        options=[
            {'label': 'UTC', 'value': 'UTC'},
            {'label': 'Local Time', 'value': 'Local'},
        ],
        value='UTC',  # Default value
        style={'width': '50%', 'margin-bottom': '20px'}
    ),
    html.Div(id='status-table-device'),
    dcc.Graph(id='power-trend-line-graph-device'),
    # Add three graphs for EV at the bottom
    dcc.Graph(id='ev-power-graph'),
    dcc.Graph(id='ev-voltage-graph'),
    dcc.Graph(id='ev-current-graph'),
])

# Home Page callback
@app.callback(
    [Output('control-command-display-home', 'children'),
     Output('total-consumption-line-graph-home', 'figure'),
     Output('priority-trend-line-graph-home', 'figure'),
     Output('ev-power-display-home', 'children'),
     Output('ev-status-light-home', 'style')],
    [Input('interval-component-home', 'n_intervals'),
     Input('timezone-selector-home', 'value')]
)
def update_home_page(n, timezone):
    data_list = fetch_data_last_20_minutes()

    if not data_list:
        return "No control command available.", {}, {}, "No Data", {'backgroundColor': 'grey'}

    # Convert timestamps based on selected timezone
    data_list = convert_timestamps(data_list, timezone)

    # Extract control commands and guess missing thresholds
    control_commands = [data.get('Control', {}).get('Django', {}).get('cmd', None) for _, data in data_list]
    guessed_commands = guess_missing_thresholds(control_commands)

    # Parse thresholds and prepare for display
    thresholds_list = []
    combined_threshold = None
    for command in guessed_commands:
        if isinstance(command, list) and len(command) == 2:
            thresholds_list.append({'total': command[1]})
            combined_threshold = command[1]  # Use this as the total consumption threshold
        elif isinstance(command, dict):
            thresholds_list.append({priority: cmd[1] for priority, cmd in command.items()})
            combined_threshold = sum(cmd[1] for cmd in command.values())  # Combine thresholds for total consumption
        else:
            thresholds_list.append(None)

    guessed_thresholds_list = guess_missing_thresholds(thresholds_list)

    # Prepare display for thresholds
    if guessed_thresholds_list[0]:
        if 'total' in guessed_thresholds_list[0]:
            thresholds_display = f"Current Threshold: Total Consumption <= {guessed_thresholds_list[0]['total']} W"
        else:
            thresholds_display = "Current Thresholds: " + ", ".join(
                [f"Priority {priority} <= {threshold} W" for priority, threshold in guessed_thresholds_list[0].items()]
            )
    else:
        thresholds_display = "No valid threshold command available."
        
    priority_thresholds_list, total_thresholds_list=guess_missing_thresholds_spit(control_commands)

    # Process data for total consumption and priority consumption
    priority_trend_list = []

    for ts, data in data_list:
        for monitor, buildings in data.get('Monitor', {}).items():
            for building, devices in buildings.items():
                for device, metrics in devices.items():
                    priority_trend_list.append({
                        'timestamp': ts,
                        'priority': metrics.get('priority'),
                        'power': metrics.get('power')
                    })
        # Handle EV data
        for ev_device, metrics in data.get('Monitor', {}).get('EV', {}).items():
            priority_trend_list.append({
                'timestamp': ts,
                'priority': metrics.get('priority'),
                'power': metrics.get('power')
            })

    df_priority_trend = pd.DataFrame(priority_trend_list)

    # Create the priority trend line graph
    priority_trend_figure = {
        'data': [],
        'layout': {
            'title': "Total Power Consumption by Priority Over Last 20 Minutes",
            'xaxis': {'title': 'Time'},
            'yaxis': {'title': 'Total Power Consumption (W)'},
        }
    }

    df_priority_grouped = df_priority_trend.groupby(['timestamp', 'priority']).sum().reset_index()
    color_map = ['red', 'green', 'blue', 'orange', 'purple']  # Example colors for different thresholds
    color_idx = 0
    for priority in df_priority_grouped['priority'].unique():
        priority_data = df_priority_grouped[df_priority_grouped['priority'] == priority]
        priority_trend_figure['data'].append({
            'x': priority_data['timestamp'],
            'y': priority_data['power'],
            'mode': 'lines',
            'name': f'Priority {priority}',
            'line': {'color': color_map[color_idx], 'width':1.5},
            'opacity': 0.7,  # Slightly transparent
            
        })
        color_idx += 1

    # Ensure that only one threshold per priority group is displayed
    unique_thresholds = {}
    for thresholds in guessed_thresholds_list:
        if thresholds and 'total' not in thresholds:
            for priority, threshold in thresholds.items():
                unique_thresholds[priority] = threshold

    # Add threshold lines to priority trend graph
    color_idx = 0
    for priority, threshold in priority_thresholds_list.items():
        priority_trend_figure['data'].append({
            'x': df_priority_grouped['timestamp'].unique(),
            'y': threshold,
            'mode': 'lines',
            'name': f'Threshold Priority {priority}',
            'line': {'dash': 'dash', 'color': color_map[color_idx ], 'width': 2.5 },
            'opacity': 0.7,  # Slightly transparent
            
           
        })
        color_idx += 1

    # Calculate total power consumption by summing up all priority groups
    df_total_consumption = df_priority_grouped.groupby('timestamp').sum().reset_index()

    # Create the total consumption line graph
    total_consumption_figure = {
        'data': [
            {'x': df_total_consumption['timestamp'], 'y': df_total_consumption['power'], 'mode': 'lines', 'name': 'Total Consumption'},
        ],
        'layout': {
            'title': "Total Power Consumption Over Last 20 Minutes",
            'xaxis': {'title': 'Time'},
            'yaxis': {'title': 'Total Power Consumption (W)','range': [0, 7000]},
            
        }
    }

    # Add combined threshold line to total consumption graph if applicable
    if total_thresholds_list:
        total_consumption_figure['data'].append({
            'x': df_total_consumption['timestamp'].unique(),
            'y': total_thresholds_list,
            'mode': 'lines',
            'name': f'Combined Threshold',
            'line': {'dash': 'dash', 'color': 'red'}
        })
    
    # Prepare EV power consumption display and status light
    latest_ev_data = priority_trend_list[-1] if priority_trend_list else None
    ev_power_display = f"EV Power: {latest_ev_data['power']} W" if latest_ev_data else "No Data"
    ev_status_light_style = {'backgroundColor': status_colors[1] if latest_ev_data and latest_ev_data['power'] > 0 else 'red',
                             'width': '20px', 'height': '20px', 'borderRadius': '50%'}

    return thresholds_display, total_consumption_figure, priority_trend_figure, ev_power_display, ev_status_light_style

# Device Page callback
@app.callback(
    [Output('status-table-device', 'children'),
     Output('power-trend-line-graph-device', 'figure'),
     Output('ev-power-graph', 'figure'),
     Output('ev-voltage-graph', 'figure'),
     Output('ev-current-graph', 'figure')],
    [Input('interval-component-device', 'n_intervals'),
     Input('timezone-selector-device', 'value')]
)
def update_device_page(n, timezone):
    data_list = fetch_data_last_20_minutes()

    if not data_list:
        return {}, {}, {}, {}, {}

    # Convert timestamps based on selected timezone
    data_list = convert_timestamps(data_list, timezone)

    # Prepare data for status bar graph and device power trends
    latest_ts, latest_data = data_list[0]
    status_data_list = []
    power_trend_list = []
    ev_power_list = []
    ev_voltage_list = []
    ev_current_list = []

    # Extracting device and EV data
    for ts, data in data_list:
        for monitor, buildings in data.get('Monitor', {}).items():
            for building, devices in buildings.items():
                for device, metrics in devices.items():
                    power_trend_list.append({
                        'timestamp': ts,
                        'device': device,
                        'power': metrics.get('power')
                    })
        
        # Handle EV data
        for ev_device, metrics in data.get('Monitor', {}).get('EV', {}).items():
            ev_power_list.append({'timestamp': ts, 'power': metrics['power']})
            ev_voltage_list.append({'timestamp': ts, 'voltage': metrics['voltage']})
            ev_current_list.append({'timestamp': ts, 'current': metrics['current']})

    # Prepare the status table
    for monitor, buildings in latest_data.get('Monitor', {}).items():
        for building, devices in buildings.items():
            for device, metrics in devices.items():
                status_data_list.append({
                    'device': device,
                    'status': metrics.get('status'),
                    'priority': metrics.get('priority'),
                    'power': round(metrics.get('power'), 1),
                    'maxpower': round(metrics.get('maxpower'), 1)
                })
    df_status = pd.DataFrame(status_data_list)
    df_power_trend = pd.DataFrame(power_trend_list)

    # Create the status table
    status_table = dash_table.DataTable(
        columns=[{'name': 'Device', 'id': 'device'}, {'name': 'Priority', 'id': 'priority'},
                 {'name': 'Status', 'id': 'status'}, {'name': 'Power (W)', 'id': 'power'}, {'name': 'Max Power (W)', 'id': 'maxpower'}],
        data=df_status.to_dict('records'),
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{status} = 0',  # When status is 0 (Off)
                    'column_id': 'priority'
                },
                'backgroundColor': status_colors[0],
                'color': 'black',
            },
            {
                'if': {
                    'filter_query': '{status} = 1',  # When status is 1 (On)
                    'column_id': 'priority'
                },
                'backgroundColor': status_colors[1],
                'color': 'black',
            },
            {
                'if': {
                    'filter_query': '{status} = 8',  # When status is 8 (Standby)
                    'column_id': 'priority'
                },
                'backgroundColor': status_colors[8],
                'color': 'black',
            },
            {
                'if': {
                    'filter_query': '{status} = 11',  # When status is 11 (Communication Error)
                    'column_id': 'priority'
                },
                'backgroundColor': status_colors[11],
                'color': 'black',
            },
        ],
        style_cell={
            'font_family': 'Source Code Pro',
            'font_size': '20px',
            'text_align': 'center',
            'padding': '5px'
        },
        style_header={
            'backgroundColor': 'lightblue',
            'fontWeight': 'bold'
        }
    )

    # Create the power trend line graph for devices
    power_trend_figure = {
        'data': [],
        'layout': {
            'title': "Device Power Consumption Trend Over Last 20 Minutes",
            'xaxis': {'title': 'Time'},
            'yaxis': {'title': 'Power Consumption (W)'},
        }
    }

    for device in df_power_trend['device'].unique():
        device_data = df_power_trend[df_power_trend['device'] == device]
        power_trend_figure['data'].append({
            'x': device_data['timestamp'],
            'y': device_data['power'],
            'mode': 'lines',
            'name': device
        })

    # Create graphs for EV power, voltage, and current
    ev_power_df = pd.DataFrame(ev_power_list)
    ev_voltage_df = pd.DataFrame(ev_voltage_list)
    ev_current_df = pd.DataFrame(ev_current_list)

    ev_power_figure = {
        'data': [
            {'x': ev_power_df['timestamp'], 'y': ev_power_df['power'], 'mode': 'lines', 'name': 'EV Power Consumption'}
        ],
        'layout': {'title': 'EV Power Consumption Over Time', 'xaxis': {'title': 'Time'}, 'yaxis': {'title': 'Power (W)'}}
    }

    ev_voltage_figure = {
        'data': [
            {'x': ev_voltage_df['timestamp'], 'y': ev_voltage_df['voltage'], 'mode': 'lines', 'name': 'EV Voltage'}
        ],
        'layout': {'title': 'EV Voltage Over Time', 'xaxis': {'title': 'Time'}, 'yaxis': {'title': 'Voltage (V)'}}
    }

    ev_current_figure = {
        'data': [
            {'x': ev_current_df['timestamp'], 'y': ev_current_df['current'], 'mode': 'lines', 'name': 'EV Current'}
        ],
        'layout': {'title': 'EV Current Over Time', 'xaxis': {'title': 'Time'}, 'yaxis': {'title': 'Current (A)'}}
    }

    return status_table, power_trend_figure, ev_power_figure, ev_voltage_figure, ev_current_figure

# Update page layout based on URL
@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/device-page':
        return device_layout
    else:
        return home_layout

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
