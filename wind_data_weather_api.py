import requests
import pgeocode

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

# Build the API request URL and parameters
api_url = "https://api.open-meteo.com/v1/forecast"
params = {
    'latitude': latitude,
    'longitude': longitude,
    'hourly': 'windspeed_10m,winddirection_10m',
    'windspeed_unit': 'mph',  # Use 'mph' for wind speed in miles per hour
    'timezone': 'auto'        # Automatically adjusts to the local timezone
}

# Make the API request
response = requests.get(api_url, params=params)

# Check for a successful response
if response.status_code == 200:
    data = response.json()
    # Extract the hourly data
    times = data['hourly']['time']
    wind_speeds = data['hourly']['windspeed_10m']
    wind_directions = data['hourly']['winddirection_10m']

    # Print the hourly wind data
    print("\nHourly Wind Data:")
    for time, speed, direction in zip(times, wind_speeds, wind_directions):
        print(f"Time: {time}, Wind Speed: {speed} mph, Wind Direction: {direction}°")
else:
    print(f"Error fetching data: HTTP {response.status_code}")
