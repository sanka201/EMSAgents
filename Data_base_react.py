import mysql.connector
import json
import csv
import os

# Create a directory to store the output files
output_dir = 'output_data'
os.makedirs(output_dir, exist_ok=True)

# Connect to MySQL
connection = mysql.connector.connect(
    host='192.168.10.52',
    user='SANKA',
    password='3Sssmalaka@!',
    database='GLEAMM_NIRE'
)

# Prepare a list to store processed data
processed_data = []
try:
    cursor = connection.cursor()
    # Query to get the JSON data from the past 2 hours
    cursor.execute("""
        SELECT ts, topic_id, value_string 
        FROM data 
        WHERE topic_id = 5 AND ts >= NOW() - INTERVAL 2 HOUR 
        ORDER BY ts DESC
    """)
    rows = cursor.fetchall()

    # Initialize dictionaries to store processed data by w_key
    w_key_data = {}
    total_power_consumption = {}
    priority_power_consumption = {}
    control_command_per_priority = {}
    control_command_total = {}
    all_priorities = set()

    for row in reversed(rows):
        ts = row[0]
        id = row[1]
        json_data = json.loads(row[2])  # Load the JSON string into a Python dictionary

        # Navigate to the specific parts of the JSON
        monitor_data = json_data.get('Monitor', {}).get('building540', {})
        control_data = json_data.get('Control', {}).get('Django', {}).get('cmd', {})
        # Extract control commands for total power consumption
        control_command_total[ts] = None
        if isinstance(control_data, list) and control_data[0] == 'lpc':
                control_command_total[ts] = control_data[1]

        # Iterate over each device in the monitor_data
        for device, device_data_dict in monitor_data.items():
            for w_key, w_values in device_data_dict.items():
                identifier = f"building540/{device}/{w_key}"
                power = w_values.get('power', 0.0)
                status = w_values.get('status', None)
                priority = w_values.get('priority', None)
                command = w_values.get('command', None)

                # Track all priority levels
                if priority is not None:
                    all_priorities.add(priority)

                # Create the full path directory for each identifier if it doesn't exist
                device_dir = os.path.join(output_dir, f'building540/{device}')
                os.makedirs(device_dir, exist_ok=True)

                # Store data in the w_key-specific list
                if w_key not in w_key_data:
                    w_key_data[w_key] = []

                w_key_data[w_key].append({
                    'ts': ts,
                    'id': id,
                    'identifier': identifier,
                    'power': power,
                    'status': status,
                    'priority': priority,
                    'command': command
                })

                # Update total power consumption
                if ts not in total_power_consumption:
                    total_power_consumption[ts] = 0.0
                total_power_consumption[ts] += power

                # Update power consumption per priority
                if ts not in priority_power_consumption:
                    priority_power_consumption[ts] = {}
                if ts not in control_command_per_priority:
                    control_command_per_priority[ts] = {}
                if priority not in priority_power_consumption[ts]:
                    priority_power_consumption[ts][priority] = 0.0
                   # control_command_per_priority[ts][priority] = None

                priority_power_consumption[ts][priority] += power

                # Extract control commands per priority
                if isinstance(control_data, dict) :
                    for key in control_data:
                        control_command_per_priority[ts][key] = control_data[key][1]
                    control_command_total[ts]=sum(control_command_per_priority[ts].values())
                #print(control_command_per_priority)

finally:
    cursor.close()
    connection.close()

# Save each w_key's data to separate CSV files under their respective directories
for w_key, data in w_key_data.items():
    # Determine the device directory based on the first entry's identifier
    first_entry = data[0]
    device_path = '/'.join(first_entry['identifier'].split('/')[:-1])  # Get path without the w_key
    csv_file_name = os.path.join(output_dir, device_path, f'{w_key}.csv')

    # Ensure the directory exists
    os.makedirs(os.path.dirname(csv_file_name), exist_ok=True)

    with open(csv_file_name, 'w', newline='') as csvfile:
        fieldnames = ['ts', 'id', 'identifier', 'power', 'status', 'priority', 'command']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for entry in data:
            writer.writerow(entry)

    print(f"Data for {w_key} has been successfully saved to {csv_file_name}.")

# Save total power consumption and control command to a CSV file in the base directory
csv_file_name = os.path.join(output_dir, 'total_power_consumption.csv')
with open(csv_file_name, 'w', newline='') as csvfile:
    fieldnames = ['ts', 'total_power', 'control_command']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for ts, total_power in total_power_consumption.items():
        writer.writerow({'ts': ts, 'total_power': total_power, 'control_command': control_command_total.get(ts, None)})
        #print(control_command_total)

print(f"Total power consumption and control command has been successfully saved to {csv_file_name}.")

# Prepare to save power consumption per priority group with separate columns for each priority and control command
priority_columns = sorted(all_priorities)  # Sort priorities for consistent column ordering
priority_fieldnames = ['ts'] + [f'priority_{p}_power' for p in priority_columns] + [f'priority_{p}_control' for p in priority_columns]

csv_file_name = os.path.join(output_dir, 'priority_power_consumption.csv')
with open(csv_file_name, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=priority_fieldnames)

    writer.writeheader()
    for ts, priorities in priority_power_consumption.items():
        row = {'ts': ts}
        for priority in priority_columns:
            row[f'priority_{priority}_power'] = priorities.get(priority, 0.0)
            row[f'priority_{priority}_control'] = control_command_per_priority.get(ts, {}).get(str(priority))
            #print(priority,control_command_per_priority.get(ts, {}).get(str(priority)))
        writer.writerow(row)

print(f"Power consumption per priority group and control command has been successfully saved to {csv_file_name}.")