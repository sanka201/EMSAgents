# weather_gov_weather.py

import requests
from datetime import datetime, timedelta, timezone
import logging
import sqlite3

# Define the Power Curve (Replace with your actual turbine's power curve)
POWER_CURVE = [
    (0, 0),
    (3, 0),
    (5, 1),
    (7, 3),
    (9, 5),
    (11, 7),
    (13, 9),
    (15, 10),
    (17, 10),
    (19, 10),
    (21, 10),
    (23, 10),
    (25, 0),
    (30, 0)
]

def setup_logging():
    """
    Set up logging configuration.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

def geocode_zip(zip_code):
    """
    Convert a US ZIP code to latitude and longitude using Zippopotam.us API.
    
    Args:
        zip_code (str): The ZIP code to geocode.
        
    Returns:
        tuple: (latitude, longitude) as floats if successful, else (None, None).
    """
    GEOCODING_API_URL = f"http://api.zippopotam.us/us/{zip_code}"
    try:
        response = requests.get(GEOCODING_API_URL, headers={"User-Agent": "Python Script"})
        if response.status_code == 200:
            data = response.json()
            place = data['places'][0]
            latitude = float(place['latitude'])
            longitude = float(place['longitude'])
            logging.info(f"Geocoded ZIP {zip_code}: Latitude={latitude}, Longitude={longitude}")
            return latitude, longitude
        else:
            logging.error(f"Geocoding API returned status code {response.status_code} for ZIP code {zip_code}")
            logging.error(f"Response Content: {response.text}")
            return None, None
    except Exception as e:
        logging.error(f"Exception during geocoding: {e}")
        return None, None

def initialize_database(db_name='weather_data.db'):
    """
    Initialize the SQLite database with required tables.
    
    Args:
        db_name (str): Name of the SQLite database file.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Create table for current weather
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS current_weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zip_code TEXT NOT NULL,
            temperature REAL,
            wind_speed REAL,
            wind_direction TEXT,
            power_output REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create table for daily forecast weather
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forecast_weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zip_code TEXT NOT NULL,
            date TEXT,
            temperature REAL,
            wind_speed REAL,
            wind_direction TEXT,
            short_forecast TEXT,
            power_output REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create table for hourly forecast weather
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hourly_forecast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zip_code TEXT NOT NULL,
            forecast_time TEXT,
            temperature REAL,
            wind_speed REAL,
            wind_direction TEXT,
            short_forecast TEXT,
            power_output REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logging.info("Initialized the SQLite database with necessary tables.")

def calculate_power_output(wind_speed, power_curve=POWER_CURVE):
    """
    Calculate the power output based on wind speed using the turbine's power curve.
    
    Args:
        wind_speed (float): Wind speed in mph.
        power_curve (list): List of tuples containing wind speed and power output.
        
    Returns:
        float: Power output in kW.
    """
    # Handle wind speeds below the first point
    if wind_speed < power_curve[0][0]:
        return 0.0
    # Handle wind speeds above the last point
    if wind_speed > power_curve[-1][0]:
        return 0.0
    # Iterate through the power curve to find the correct interval
    for i in range(len(power_curve) - 1):
        ws1, pw1 = power_curve[i]
        ws2, pw2 = power_curve[i + 1]
        if ws1 <= wind_speed <= ws2:
            if ws2 - ws1 == 0:
                return pw1
            # Linear interpolation
            return pw1 + (pw2 - pw1) * (wind_speed - ws1) / (ws2 - ws1)
    return 0.0

def insert_current_weather(db_name, zip_code, temperature, wind_speed, wind_direction):
    """
    Insert current weather data into the database.
    
    Args:
        db_name (str): Name of the SQLite database file.
        zip_code (str): The ZIP code.
        temperature (float): Current temperature.
        wind_speed (float): Current wind speed.
        wind_direction (str): Current wind direction.
    """
    power_output = calculate_power_output(wind_speed)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO current_weather (zip_code, temperature, wind_speed, wind_direction, power_output)
        VALUES (?, ?, ?, ?, ?)
    ''', (zip_code, temperature, wind_speed, wind_direction, power_output))
    conn.commit()
    conn.close()
    logging.info("Inserted current weather data into the database.")

def insert_forecast_weather(db_name, zip_code, date, temperature, wind_speed, wind_direction, short_forecast):
    """
    Insert daily forecast weather data into the database.
    
    Args:
        db_name (str): Name of the SQLite database file.
        zip_code (str): The ZIP code.
        date (str): Date of the forecast (YYYY-MM-DD).
        temperature (float): Forecasted temperature.
        wind_speed (float): Forecasted wind speed.
        wind_direction (str): Forecasted wind direction.
        short_forecast (str): Short description of the forecast.
    """
    power_output = calculate_power_output(wind_speed)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO forecast_weather (zip_code, date, temperature, wind_speed, wind_direction, short_forecast, power_output)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (zip_code, date, temperature, wind_speed, wind_direction, short_forecast, power_output))
    conn.commit()
    conn.close()
    logging.info(f"Inserted daily forecast weather data for {date} into the database.")

def insert_hourly_forecast(db_name, zip_code, forecast_time, temperature, wind_speed, wind_direction, short_forecast):
    """
    Insert hourly forecast weather data into the database.
    
    Args:
        db_name (str): Name of the SQLite database file.
        zip_code (str): The ZIP code.
        forecast_time (str): Date and time of the forecast (YYYY-MM-DD HH:MM).
        temperature (float): Forecasted temperature.
        wind_speed (float): Forecasted wind speed.
        wind_direction (str): Forecasted wind direction.
        short_forecast (str): Short description of the forecast.
    """
    power_output = calculate_power_output(wind_speed)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO hourly_forecast (zip_code, forecast_time, temperature, wind_speed, wind_direction, short_forecast, power_output)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (zip_code, forecast_time, temperature, wind_speed, wind_direction, short_forecast, power_output))
    conn.commit()
    conn.close()
    logging.info(f"Inserted hourly forecast weather data for {forecast_time} into the database.")

def clear_current_weather(db_name, zip_code):
    """
    Delete existing current weather data for the given ZIP code.
    
    Args:
        db_name (str): Name of the SQLite database file.
        zip_code (str): The ZIP code.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM current_weather WHERE zip_code = ?', (zip_code,))
    count_before = cursor.fetchone()[0]
    
    cursor.execute('DELETE FROM current_weather WHERE zip_code = ?', (zip_code,))
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    logging.info(f"Cleared {deleted} existing current weather records for ZIP code {zip_code} (Before: {count_before})")

def clear_forecast_weather(db_name, zip_code):
    """
    Delete existing daily forecast weather data for the given ZIP code.
    
    Args:
        db_name (str): Name of the SQLite database file.
        zip_code (str): The ZIP code.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM forecast_weather WHERE zip_code = ?', (zip_code,))
    count_before = cursor.fetchone()[0]
    
    cursor.execute('DELETE FROM forecast_weather WHERE zip_code = ?', (zip_code,))
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    logging.info(f"Cleared {deleted} existing daily forecast weather records for ZIP code {zip_code} (Before: {count_before})")

def clear_hourly_forecast(db_name, zip_code):
    """
    Delete existing hourly forecast weather data for the given ZIP code.
    
    Args:
        db_name (str): Name of the SQLite database file.
        zip_code (str): The ZIP code.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM hourly_forecast WHERE zip_code = ?', (zip_code,))
    count_before = cursor.fetchone()[0]
    
    cursor.execute('DELETE FROM hourly_forecast WHERE zip_code = ?', (zip_code,))
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    logging.info(f"Cleared {deleted} existing hourly forecast weather records for ZIP code {zip_code} (Before: {count_before})")

def fetch_weather_gov_data(latitude, longitude):
    """
    Fetch current and forecast weather data from weather.gov API.
    
    Args:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        
    Returns:
        dict: Parsed weather data containing current and forecast information.
    """
    try:
        # Step 1: Get the grid endpoint
        points_url = f"https://api.weather.gov/points/{latitude},{longitude}"
        logging.info(f"Fetching grid endpoint from URL: {points_url}")
        response = requests.get(points_url, headers={"User-Agent": "Python Script"})
        if response.status_code != 200:
            logging.error(f"Failed to fetch grid endpoint: {response.status_code}")
            logging.error(f"Response Content: {response.text}")
            return None
        points_data = response.json()
        forecast_url = points_data['properties'].get('forecast')
        forecast_hourly_url = points_data['properties'].get('forecastHourly')
        
        if not forecast_url or not forecast_hourly_url:
            logging.error("Forecast URLs not found in points data.")
            return None
        
        logging.info(f"Forecast URL obtained: {forecast_url}")
        logging.info(f"Forecast Hourly URL obtained: {forecast_hourly_url}")
        
        # Step 2: Get the daily forecast data
        forecast_response = requests.get(forecast_url, headers={"User-Agent": "Python Script"})
        if forecast_response.status_code != 200:
            logging.error(f"Failed to fetch forecast data: {forecast_response.status_code}")
            logging.error(f"Response Content: {forecast_response.text}")
            return None
        forecast_data = forecast_response.json()
        
        # Step 3: Get the hourly forecast data
        forecast_hourly_response = requests.get(forecast_hourly_url, headers={"User-Agent": "Python Script"})
        if forecast_hourly_response.status_code != 200:
            logging.error(f"Failed to fetch forecast hourly data: {forecast_hourly_response.status_code}")
            logging.error(f"Response Content: {forecast_hourly_response.text}")
            return None
        forecast_hourly_data = forecast_hourly_response.json()
        
        # Step 4: Parse the forecast for the next 3 days (daily)
        periods = forecast_data['properties']['periods']
        weather_data = {
            'current': {},
            'forecast_daily': [],
            'forecast_hourly': []
        }
        
        current_time = datetime.now(timezone.utc)
        for period in periods:
            forecast_time = datetime.strptime(period['startTime'], "%Y-%m-%dT%H:%M:%S%z")
            if forecast_time < current_time:
                continue
            day_diff = (forecast_time.date() - current_time.date()).days
            if day_diff > 3:
                break
            if day_diff == 0 and not weather_data['current']:
                # Current conditions
                weather_data['current']['temperature'] = period['temperature']
                weather_data['current']['wind_speed'] = parse_wind_speed(period['windSpeed'])
                weather_data['current']['wind_direction'] = period['windDirection']
            elif 1 <= day_diff <= 3:
                # Forecast conditions
                weather_data['forecast_daily'].append({
                    'date': forecast_time.strftime("%Y-%m-%d"),
                    'temperature': period['temperature'],
                    'wind_speed': parse_wind_speed(period['windSpeed']),
                    'wind_direction': period['windDirection'],
                    'short_forecast': period['shortForecast']
                })
        
        # Step 5: Parse the hourly forecast for the next 3 days
        hourly_periods = forecast_hourly_data['properties']['periods']
        for hour in hourly_periods:
            forecast_time = datetime.strptime(hour['startTime'], "%Y-%m-%dT%H:%M:%S%z")
            if forecast_time < current_time:
                continue
            if (forecast_time - current_time).days >= 3:
                break
            weather_data['forecast_hourly'].append({
                'forecast_time': forecast_time.strftime("%Y-%m-%d %H:%M"),
                'temperature': hour['temperature'],
                'wind_speed': parse_wind_speed(hour['windSpeed']),
                'wind_direction': hour['windDirection'],
                'short_forecast': hour['shortForecast']
            })
        
        logging.info("Successfully fetched and parsed weather data.")
        return weather_data
    except:
        pass

def parse_wind_speed(wind_speed_str):
    """
    Parse wind speed string to float (mph).
    
    Args:
        wind_speed_str (str): Wind speed string from API (e.g., "10 mph").
        
    Returns:
        float: Wind speed in mph.
    """
    try:
        speed = float(wind_speed_str.split()[0])
        return speed
    except:
        return None

def main():
    setup_logging()
    
    # Configuration
    zip_code = "79416"  # Replace with desired ZIP code
    db_name = 'weather_data.db'
    
    # Initialize database
    initialize_database(db_name)
    
    # Geocode ZIP code
    latitude, longitude = geocode_zip(zip_code)
    if latitude is None or longitude is None:
        logging.error("Geocoding failed. Exiting.")
        return
    
    # Clear existing data
    clear_current_weather(db_name, zip_code)
    clear_forecast_weather(db_name, zip_code)
    clear_hourly_forecast(db_name, zip_code)
    
    # Fetch weather data
    weather_data = fetch_weather_gov_data(latitude, longitude)
    if weather_data is None:
        logging.error("Failed to fetch weather data. Exiting.")
        return
    
    # Insert current weather
    current = weather_data['current']
    if current:
        insert_current_weather(
            db_name=db_name,
            zip_code=zip_code,
            temperature=current['temperature'],
            wind_speed=current['wind_speed'],
            wind_direction=current['wind_direction']
        )
    
    # Insert daily forecast weather
    for forecast in weather_data['forecast_daily']:
        insert_forecast_weather(
            db_name=db_name,
            zip_code=zip_code,
            date=forecast['date'],
            temperature=forecast['temperature'],
            wind_speed=forecast['wind_speed'],
            wind_direction=forecast['wind_direction'],
            short_forecast=forecast['short_forecast']
        )
    
    # Insert hourly forecast weather
    for forecast in weather_data['forecast_hourly']:
        insert_hourly_forecast(
            db_name=db_name,
            zip_code=zip_code,
            forecast_time=forecast['forecast_time'],
            temperature=forecast['temperature'],
            wind_speed=forecast['wind_speed'],
            wind_direction=forecast['wind_direction'],
            short_forecast=forecast['short_forecast']
        )

if __name__ == "__main__":
    main()
