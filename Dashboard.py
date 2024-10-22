from flask import Flask
from dash import Dash, dcc, html,dash_table
from dash.dependencies import Input, Output
import mysql.connector
import pandas as pd
import json
import pytz
from datetime import datetime,timedelta
import dash_bootstrap_components as dbc
import plotly.express as px


# Sample data for the pie chart

#### to RUN the APP

### nohup gunicorn dash_app:server -w 4 -b 0.0.0.0:8050 > dash_app.log 2>&1 &
#### kill the app
####  ps aux | grep gunicorn  # Find the process ID (PID)
#### kill <PID>  # Replace <PID> with the actual PID
#### disown



# Flask setup
server = Flask(__name__)

# Dash setup
app = Dash(__name__, server=server, url_base_pathname='/', title="GNIRE-GLEAMM EMS Testing",suppress_callback_exceptions=True)
server = app.server 
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
        query =""" SELECT ts, value_string FROM GLEAMM_NIRE.data  where topic_id=5 and  ts <= UTC_TIMESTAMP()   and ts >=date_sub( UTC_TIMESTAMP() , interval 3 hour) ORDER BY ts DESC """

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
home_layout = html.Div(  
                       children=[
    html.Img(src='/assets/background.jpg', style={
            'width': '300px',  # Adjust the size as needed
            'height': '100px',
            'margin-bottom': '20px',
            'display': 'block',  # Make the image a block element
            'margin': 'auto'  # Center the image horizontally
        }),  # Replace with your image path and adjust style as needed
        html.H1("NIRE Load Priority Control Program" , style={'fontSize': 50, 'margin': '10px 0', 'text-align':'center', 'weight':'bold', 'style': 'italic','color':'#fc5603', 'text-shadow': '2px 2px 4px rgba(0, 0, 0, 0.5)' ,      'border-radius': '8px' ,    'border-bottom': '3px solid gray',  # Adds an underline with specific color and thickness
                'padding-bottom': '10px',  # Adds some spacing between the text and underline
      }),
    dcc.Link('Go to Device Page', href='/device-page'),
    dcc.Interval(
        id='interval-component-home',
        interval=40*1000,  # Update every 40 seconds
        n_intervals=0
    ),
    
        # EV Card at the top of the Home Page
 html.Div(
            style={
                'display': 'flex',
                'justifyContent': 'center',  # Center the cards
                'alignItems': 'flex-start',  # Align cards to the top
                'gap': '40px'  # Space between cards
            },
    
     children=[dbc.Card(
        dbc.CardBody([
             html.H4("EV Status", className="card-title", style={'textAlign': 'center','fontSize': 35}),
            html.Img(src='/assets/ev_image.jpg', style={'width': '350px', 'height': '250px', 'display': 'block',  # Make image a block element
                                'margin': '0 auto'}),  
            html.Div(id='ev-electrical', style={'fontSize': 35, 'margin': '5px 0', 'textAlign': 'center','whiteSpace': 'nowrap'}),
            html.Div(id='ev-power-display-home', style={'fontSize': 35, 'weight':'bold','textAlign': 'center','margin': '10px 0'}),
            html.Div(id='ev-energy-display-home', style={'fontSize': 35,'weight':'bold', 'textAlign': 'center','margin': '10px 0'}),
            html.Div(id='ev-status-display-home', style={'fontSize': 30, 'weight':'bold','textAlign': 'center','margin': '10px 0'})
            ]),
        style={'width': '18rem', 'padding': '20px','backgroundColor': 'rgba(255, 255, 255, 0.8)',      'border': '1px solid lightgray',  # Light gray border for the boundary
                        'box-shadow': '0 4px 8px rgba(0, 0, 0, 0.2)',  # Shadow for floating effect
                        'border-radius': '10px',   'flex': '1',  # Allow this card to grow equally
                        'min-width': '250px', 'border-color': '#fc5603', 'border-width':'3px'  # Rounded corners
                        }
    ),
                               dbc.Card(
                    dbc.CardBody([
                        html.H4("Grid Status", className="card-title", style={'textAlign': 'center','fontSize': 35}),
                        html.Div("Online", id='grid-status-display', style={'fontSize': 38, 'textAlign': 'center', 'color': 'green','weight':'bold',}),  # Example text and style
                        html.H4("Locational Marginal Pricing (LMP)",style={'textAlign': 'center','fontSize': 35}),
                        html.Div(id='lmp', style={'fontSize': 38, 'margin': '5px 0', 'textAlign': 'center','whiteSpace': 'nowrap', 'weight':'bold' }),
                        html.Div(id='total-instance-cost', style={'fontSize': 38, 'margin': '5px 0', 'textAlign': 'center','whiteSpace': 'nowrap'}),
                        html.Div(id='total_cost_last_hour', style={'fontSize': 38, 'margin': '5px 0', 'textAlign': 'center','whiteSpace': 'nowrap', 'weight':'bold' })
                    ]),
                    style={'width': '18rem', 'padding': '20px', 'backgroundColor': 'rgba(255, 255, 255, 0.8)',      'border': '1px solid lightgray',  # Light gray border for the boundary
                        'box-shadow': '0 4px 8px rgba(0, 0, 0, 0.2)',  # Shadow for floating effect
                        'border-radius': '10px' ,    'flex': '1',  # Allow this card to grow equally
                        'min-width': '250px',  'border-color': '#fc5603', 'border-width':'3px' # Rounded corners
                        }
                ),
                # Power Consumption Card
                dbc.Card(
                    dbc.CardBody([
                        html.H4("Power Consumption By Groups", className="card-title", style={'textAlign': 'center','fontSize': 35}),
                        html.Div(id='total-power', style={'fontSize': 34, 'margin': '5px 0', 'textAlign': 'center','whiteSpace': 'nowrap'}),
                         html.Div(id='total-energy-consumption', style={'fontSize': 34, 'margin': '5px 0', 'textAlign': 'center','whiteSpace': 'nowrap'}),
                                                # Pie chart inside the card
                        dcc.Graph(
                            id='power-consumption-pie-chart'
                        )
                      #  html.Div("75%", id='power-consumption-display', style={'fontSize': 22, 'textAlign': 'center', 'color': 'blue'})  # Example text and style
                    ]),
                    style={'width': '18rem', 'padding': '20px', 'backgroundColor': 'rgba(255, 255, 255, 0.8)',      'border': '1px solid lightgray',  # Light gray border for the boundary
                        'box-shadow': '0 4px 8px rgba(0, 0, 0, 0.2)',  # Shadow for floating effect
                        'border-radius': '10px',    'flex': '1',  # Allow this card to grow equally
                        'min-width': '250px', 'border-color': '#fc5603', 'border-width':'3px'  # Rounded corners
                        }
                )
               ]),
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
     dcc.Loading(
            id="loading-graphs",
            type="default",
            children=[
    dcc.Graph(id='total-consumption-line-graph-home'),
    dcc.Graph(id='priority-trend-line-graph-home'),])
])

# Define status colors
status_colors = {
    0: '#00e118',  # Off
    1: '#3165f8',  # On
    2: '#3165f8',  # On
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
])

# Home Page callback
@app.callback(
    [Output('control-command-display-home', 'children'),
     Output('total-consumption-line-graph-home', 'figure'),
     Output('priority-trend-line-graph-home', 'figure'),
     Output('ev-power-display-home', 'children'),
    Output('ev-energy-display-home', 'children'),
    Output('ev-status-display-home', 'children'),
    Output('ev-status-display-home', 'style'),
    Output('ev-electrical', 'children'),
    Output('power-consumption-pie-chart', 'figure'),
    Output('total-power','children' ),
    Output('lmp','children' ),
    Output('total-instance-cost','children' ),
    Output('total_cost_last_hour','children' ),
    Output('total-energy-consumption','children' )
      ],
    [Input('interval-component-home', 'n_intervals'),
     Input('timezone-selector-home', 'value')]
)
def update_home_page(n, timezone):
    data_list = fetch_data_last_20_minutes()

    if not data_list:
        return "No control command available.", {}, {}

    # Convert timestamps based on selected timezone
    data_list = convert_timestamps(data_list, timezone)

    # Extract control commands and guess missing thresholds
    control_commands = [data.get('Control', {}).get('Django', {}).get('cmd', None) for _, data in data_list]
    LMP = data_list[0][1]['LMP']
    one_hour_ago=data_list[0][0]-timedelta(hours=1)
    filtered_tuples = [tup[1]['LMP'] for tup in data_list if tup[0] >= one_hour_ago]
    LMP_average_for_last_hour=sum(filtered_tuples)/1000/len(filtered_tuples)
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
    latest_data = data_list[0]
    Evlatest=[]
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
                    'power' : round(metrics.get('power'),1)
            })
    tempdata=latest_data[1].get('Monitor', {}).get('building540',{}).get('EV',{}).get('building540/EV/JuiceBox')
    Evpower=tempdata.get('power')
    Evenergy=tempdata.get('energy')
    Evstatus=tempdata.get('status')
    Evtemerature=tempdata.get('temperature')
    Evcurrent=tempdata.get('current')
    Evvoltage=tempdata.get('voltage')
    Evfrequency=tempdata.get('frequency')      
    df_priority_trend = pd.DataFrame(priority_trend_list)
    # Create the priority trend line graph
    priority_trend_figure = {
        'data': [],
        'layout': {
             'title': {
            'text': "Total Power Consumption By Priority",  # Chart title text
            'font': {
                'size': 28,  # Title font size
                'color': 'black',  # Title font colo
                'weight': 'bold'  # Title font weight
            }
        },
            'title_font'
            'xaxis': {'title': 'Time','titlefont': {'size': 24}, 'tickfont': {'size': 25,'weight': 'bold'}, },
            'yaxis': {'title': 'Total Power Consumption (W)','titlefont': {'size': 24}, 'tickfont': {'size': 25,'weight': 'bold'}, },
            'margin': {'l': 100, 'r': 40, 't': 60, 'b': 60} ,
              'height': 500 ,
               'legend': {
                'font': {'size': 19, 'color': '#0e0180','weight': 'bold'}}
        }
    }
    
    df_priority_grouped = df_priority_trend.groupby(['timestamp', 'priority']).sum().reset_index()
    pidata = {
    'Group': [],
    'Consumption': []
    }
    color_map = ['red', 'green', 'blue', 'orange', 'purple']  # Example colors for different thresholds
    color_idx = 0
    for priority in df_priority_grouped['priority'].unique():
        priority_data = df_priority_grouped[df_priority_grouped['priority'] == priority]
        try:
            if priority==0:
                 priority_trend_figure['data'].append({
                    'x': priority_data['timestamp'],
                    'y': priority_data['power'],
                    'mode': 'lines',
                    'name': f'Differable Group',
                    'line': {'color': '#e303fc', 'width':1.5},
                    'opacity': 0.7,  # Slightly transparent
                    
                })               
            else:
                priority_trend_figure['data'].append({
                    'x': priority_data['timestamp'],
                    'y': priority_data['power'],
                    'mode': 'lines',
                    'name': f'Group {priority}',
                    'line': {'color': color_map[color_idx], 'width':1.5},
                    'opacity': 0.7,  # Slightly transparent
                    
                })
        except:
            pass
        color_idx += 1
        pidata['Group'].append('Differable Group') if priority==0 else pidata['Group'].append('Group'+str(priority))
        pidata['Consumption'].append(df_priority_grouped[df_priority_grouped['priority'] == priority]['power'].iloc[-1])
    
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
             'title': {
            'text': "Total Power Consumption",  # Chart title text
            'font': {
                'size': 28,  # Title font size
                'color': 'black',  # Title font colo
                'weight': 'bold'  # Title font weight
            }
        },
            'xaxis': {'title': 'Time', 'titlefont': {'size': 24}, 'tickfont': {'size': 25, 'weight': 'bold'}, },
            'yaxis': {'title': 'Total Power Consumption (W)','range': [0, 11500],'titlefont': {'size': 24}, 'tickfont': {'size': 25,'weight': 'bold'}, },
                        'margin': {'l': 100, 'r': 40, 't': 60, 'b': 60} ,
                         'height': 500 ,
                           'legend': {
                'font': {'size': 19, 'color': '#0e0180','weight': 'bold'}}
        }
    }
    Latest_power_value =df_total_consumption['power'].iloc[-1]
    last_hour_data = df_total_consumption[(df_total_consumption['timestamp'] > one_hour_ago) & (df_total_consumption['timestamp'] <= df_total_consumption['timestamp'].max())]
    Last_hour_power_consumption=last_hour_data['power'].sum()/1000* 40 / 3600
    Last_hour_usage_cost=LMP_average_for_last_hour*Last_hour_power_consumption
    Last_hour_usage_cost_text= 'Hourly Cost: ' + str(round(Last_hour_usage_cost,4))+ ' $' 
    print('Last Hour Cost of Usage ', Last_hour_usage_cost)
    pidata['Consumption']= pidata['Consumption']*0 if Latest_power_value==0 else pidata['Consumption']/Latest_power_value*100
    Latest_power_value_text= 'Total Power Consumption: '+str(round(Latest_power_value/1000,2))+' kW'
    #print(df_total_consumption['power'].iloc[-1],df_priority_grouped[df_priority_grouped['priority'] == 0]['power'].iloc[-1],df_priority_grouped[df_priority_grouped['priority'] == 0]['power'].iloc[-1],df_priority_grouped[df_priority_grouped['priority'] == 1]['power'].iloc[-1],df_priority_grouped[df_priority_grouped['priority'] == 2]['power'].iloc[-1],df_priority_grouped['priority'].unique())

    # Add combined threshold line to total consumption graph if applicable

    if total_thresholds_list:
        total_consumption_figure['data'].append({
            'x': df_total_consumption['timestamp'].unique(),
            'y': total_thresholds_list,
            'mode': 'lines',
            'name': f'Combined Threshold',
            'line': {'dash': 'dash', 'color': 'red'}
        })
        
    # Create a pie chart using Plotly Express
    fig1 = px.pie(
    pidata, 
    names='Group', 
    values='Consumption', 
    hole=0,  # Donut chart style with a hole in the middle
    color_discrete_sequence=['green','blue', 'orange','#e303fc']  # Custom colors for each slice
    )
  
    # Customize the pie chart font and text properties
    fig1.update_traces(
        textinfo='percent',  # Display percentage and label
        textfont=dict(size=25, color='black', weight='bold'),
        pull=[0.01, 0.01, 0.01, 0.01] 
    )
    
    # Update layout for overall chart font and title
    fig1.update_layout(
        title_font_size=28,  # Increase title font size
        font=dict(
            family='Courier New, monospace',  # Global font family for the chart
            size=18,  # Global font size for other elements like the legend
            color='black'  # Global font color
        ),
        legend=dict(font=dict(size=24)) , # Increase legend font size

    )
        
            # Prepare EV power consumption display and status light
    # latest_ev_data = priority_trend_list[-1] if priority_trend_list else None
    ev_power_display = f"EV Power: {round(Evpower/1000,2)} kW" 
    ev_status_light_style = {'backgroundColor': status_colors[11] if Evpower > 0 else 'green',
                              'width': '20px', 'height': '20px', 'borderRadius': '50%'}
    if Evstatus ==0:
        ev_status_display="Status: Available"
    elif Evstatus ==1:
        ev_status_display = "Status: Occupied (Charging stopped)"
    else:
        ev_status_display = "Status: Occupied (Charging) "
        
    
    instance_cost_text= 'Instantaneous Electricity Cost: '+ str(round(LMP/1000*Latest_power_value/1000*40/3600,5)) + ' $'
    return [thresholds_display, total_consumption_figure, priority_trend_figure, ev_power_display,f"EV Energy Consumption: {round(Evenergy/1000,2)} kWh" ,ev_status_display, 
            {'color': 'red','fontSize': 30, 'margin': '10px 0'} if  Evstatus ==2 else  {'color':'green','fontSize': 30, 'margin': '10px 0'},f'Voltage: {Evvoltage/10}V , Current: {Evcurrent/10}A , Frequency {Evfrequency/100}Hz ',
            fig1,Latest_power_value_text, 'Unit Price: '+(str(round(LMP/1000,3))+' $/kWh'), instance_cost_text,Last_hour_usage_cost_text,
            'Total Energy Consumption: '+ str(round(Last_hour_power_consumption,2))+' kWh']
# Device Page callback
@app.callback(
    [Output('status-table-device', 'children'),
     Output('power-trend-line-graph-device', 'figure')],
    [Input('interval-component-device', 'n_intervals'),
     Input('timezone-selector-device', 'value')]
)
def update_device_page(n, timezone):
    data_list = fetch_data_last_20_minutes()

    if not data_list:
        return {}, {}

    # Convert timestamps based on selected timezone
    data_list = convert_timestamps(data_list, timezone)

    # Prepare data for status bar graph and device power trends
    latest_ts, latest_data = data_list[0]
    status_data_list = []
    power_trend_list = []

    for ts, data in data_list:
        for monitor, buildings in data.get('Monitor', {}).items():
            for building, devices in buildings.items():
                for device, metrics in devices.items():
                    power_trend_list.append({
                        'timestamp': ts,
                        'device': device,
                        'power': metrics.get('power')
                    })
    for monitor, buildings in latest_data.get('Monitor', {}).items():
        for building, devices in buildings.items():
            for device, metrics in devices.items():
                status_data_list.append({
                    'device': device,
                    'status': metrics.get('status'),
                    'priority':metrics.get('priority'),
                    'power' : round(metrics.get('power'),1),
                    'maxpower': round(metrics.get('maxpower'),1)
                })
    df_status = pd.DataFrame(status_data_list)
    df_power_trend = pd.DataFrame(power_trend_list)

    # Define the style data conditional formatting for the table
    style_data_conditional = [
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
                     {'if': {
                'filter_query': '{status} = 2',  # When status is 1 (On)
                'column_id': 'priority'
            },
            'backgroundColor': status_colors[1],
            'color': 'black',
        },   
    ]

    # Create the status table
    status_table = dash_table.DataTable(
        columns=[{'name': 'Device', 'id': 'device'},{'name': 'Priority', 'id': 'priority'},
                 {'name': 'Status', 'id': 'status'},{'name': 'Power (W)', 'id': 'power'},{'name': 'Max Power (W)', 'id': 'maxpower'}],
        data=df_status.to_dict('records'),
        style_data_conditional=style_data_conditional,
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

    # Create the power trend line graph, with a line for each device
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

    return status_table, power_trend_figure

# Update page layout based on URL
@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/device-page':
        return device_layout
    else:
        return home_layout

if __name__ == '__main__':
    #app.run_server(debug=False, host='0.0.0.0', port=8050) 
    app.run_server(debug=False)
    
