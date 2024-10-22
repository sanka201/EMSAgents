import requests
import pgeocode
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Define the ZIP code and country code
zipcode = '79416'
country = 'US'  # United States

# Initialize the geocoder
nomi = pgeocode.Nominatim(country)

# Get latitude and longitude for the ZIP code
location = nomi.query_postal_code(zipcode)
latitude = location.latitude
longitude = location.longitude

if latitude is None or longitude is None:
    print(f"Unable to find coordinates for ZIP code {zipcode}.")
    exit()

print(f"Latitude: {latitude}, Longitude: {longitude}")

# Calculate the date for tomorrow
tomorrow = datetime.now() + timedelta(days=1)
start_date = tomorrow.strftime('%Y-%m-%d')
end_date = start_date  # Since we only want data for the next day

# Build the API request URL and parameters
api_url = "https://api.open-meteo.com/v1/forecast"
params = {
    'latitude': latitude,
    'longitude': longitude,
    'hourly': 'windspeed_10m',
    'windspeed_unit': 'ms',   # Wind speed in meters per second
    'timezone': 'auto',        # Automatically adjusts to the local timezone
    'start_date': start_date,
    'end_date': end_date
}

# Make the API request
response = requests.get(api_url, params=params)

# Check for a successful response
if response.status_code == 200:
    data = response.json()
    # Extract the hourly data
    times = data['hourly']['time']
    wind_speeds = data['hourly']['windspeed_10m']
    
    # Create a DataFrame
    df = pd.DataFrame({
        'time': pd.to_datetime(times),
        'wind_speed': wind_speeds  # Wind speed in m/s
    })
    
    # Define the power curve as a DataFrame
    power_curve = pd.DataFrame({
        'wind_speed': [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        'power_output': [0, 0.5, 1.0, 2.0, 3.5, 5.0, 7.0, 9.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
    })
    
    # Interpolate the power output for each wind speed
    def get_power_output(ws):
        if ws < power_curve['wind_speed'].min():
            return 0.0
        elif ws > power_curve['wind_speed'].max():
            return power_curve['power_output'].max()
        else:
            return np.interp(ws, power_curve['wind_speed'], power_curve['power_output'])
    
    df['power_output'] = df['wind_speed'].apply(get_power_output)
    
    # Calculate energy output in kWh for each hour
    df['energy_output'] = df['power_output'] * 1  # Duration is 1 hour
    
    # Calculate total energy output over the day
    total_energy = df['energy_output'].sum()
    
    # Print the predicted power and energy output
    print(f"\nPredicted Power and Energy Output for {start_date}:")
    for index, row in df.iterrows():
        time_str = row['time'].strftime('%Y-%m-%dT%H:%M')
        wind_speed = row['wind_speed']
        power_output = row['power_output']
        energy_output = row['energy_output']
        print(f"Time: {time_str}, Wind Speed: {wind_speed:.2f} m/s, Predicted Power Output: {power_output:.2f} kW, Energy Output: {energy_output:.2f} kWh")
    
    print(f"\nTotal Predicted Energy Output for {start_date}: {total_energy:.2f} kWh")
    
    # Optional: Plot the predicted power and energy output
    fig, ax1 = plt.subplots(figsize=(12, 6))

    ax1.set_xlabel('Time')
    ax1.set_ylabel('Power Output (kW)', color='tab:blue')
    ax1.plot(df['time'], df['power_output'], marker='o', color='tab:blue', label='Power Output')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax1.legend(loc='upper left')
    plt.xticks(rotation=45)
    
    ax2 = ax1.twinx()  # Instantiate a second axes that shares the same x-axis
    ax2.set_ylabel('Energy Output (kWh)', color='tab:red')  # We already handled the x-label with ax1
    ax2.bar(df['time'], df['energy_output'], alpha=0.3, color='tab:red', label='Energy Output')
    ax2.tick_params(axis='y', labelcolor='tab:red')
    ax2.legend(loc='upper right')
    
    plt.title(f'Predicted Power and Energy Output for {start_date}')
    plt.tight_layout()
    plt.show()
else:
    print(f"Error fetching data: HTTP {response.status_code}")
