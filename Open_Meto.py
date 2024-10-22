# save_open_meteo_weather.py

import requests
from datetime import datetime, timedelta, timezone
import sqlite3
import logging

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
DATABASE_NAME = 'weather_data.db'
GEOCODING_API_URL = "http://api.zippopotam.us/us/{zipcode}"
OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"

def geocode_zip(zip_code):
    """
    Convert a US ZIP code to latitude and longitude using Zippopotam.us API.

    Args:
        zip_code (str): The ZIP code to geocode.

    Returns:
        tuple: (latitude, longitude) as floats if successful, else (None, None).
    """
    url = GEOCODING_API_URL.format(zipcode=zip_code)
    logger.info(f"Geocoding ZIP code {zip_code}...")
    try:
        response = requests.get(url, headers={"User-Agent": "Python Script"})
        if response.status_code == 200:
            data = response.json()
            place = data['places'][0]
            latitude = float(place['latitude'])
            longitude = float(place['longitude'])
            logger.info(f"Geocoded ZIP {zip_code}: Latitude={latitude}, Longitude={longitude}")
            return latitude, longitude
        else:
            logger.error(f"Geocoding API returned status code {response.status_code} for ZIP code {zip_code}")
            logger.error(f"Response Content: {response.text}")
            return None, None
    except Exception as e:
        logger.error(f"Exception during geocoding: {e}")
        return None, None

def initialize_database(db_name=DATABASE_NAME):
    """
    Initialize the SQLite database with required tables.

    Args:
        db_name (str): Name of the SQLite database file.
    """
    logger.info("Initializing the SQLite database...")
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
            solar_radiation REAL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create table for forecast weather
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forecast_weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zip_code TEXT NOT NULL,
            date TEXT,
            temperature REAL,
            wind_speed REAL,
            wind_direction TEXT,
            solar_radiation REAL,
            short_forecast TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

def insert_current_weather(db_name, zip_code, temperature, wind_speed, wind_direction, solar_radiation):
    """
    Insert current weather data into the database.

    Args:
        db_name (str): Name of the SQLite database file.
        zip_code (str): The ZIP code.
        temperature (float): Current temperature in °C.
        wind_speed (float): Current wind speed in km/h.
        wind_direction (str): Current wind direction (e.g., NW).
        solar_radiation (float): Current solar radiation in W/m².
    """
    logger.info("Inserting current weather data into the database...")
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO current_weather (zip_code, temperature, wind_speed, wind_direction, solar_radiation)
        VALUES (?, ?, ?, ?, ?)
    ''', (zip_code, temperature, wind_speed, wind_direction, solar_radiation))
    conn.commit()
    conn.close()
    logger.info("Current weather data inserted successfully.")

def insert_forecast_weather(db_name, zip_code, date, temperature, wind_speed, wind_direction, solar_radiation, short_forecast):
    """
    Insert forecast weather data into the database.

    Args:
        db_name (str): Name of the SQLite database file.
        zip_code (str): The ZIP code.
        date (str): Date of the forecast (YYYY-MM-DD).
        temperature (float): Forecasted average temperature in °C.
        wind_speed (float): Forecasted wind speed in km/h.
        wind_direction (str): Forecasted wind direction (e.g., NW).
        solar_radiation (float): Forecasted solar radiation in W/m².
        short_forecast (str): Short description of the forecast.
    """
    logger.info(f"Inserting forecast weather data for {date} into the database...")
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO forecast_weather (zip_code, date, temperature, wind_speed, wind_direction, solar_radiation, short_forecast)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (zip_code, date, temperature, wind_speed, wind_direction, solar_radiation, short_forecast))
    conn.commit()
    conn.close()
    logger.info(f"Forecast weather data for {date} inserted successfully.")

def fetch_open_meteo_data(latitude, longitude):
    """
    Fetch current and forecast weather data from Open-Meteo API.

    Args:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.

    Returns:
        dict: Parsed weather data containing current and forecast information.
    """
    logger.info("Fetching weather data from Open-Meteo API...")
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'hourly': 'temperature_2m,windspeed_10m,solar_radiation',
        'daily': 'temperature_2m_max,temperature_2m_min,windspeed_10m_max,shortwave_radiation_sum',
        'current_weather': 'true',  # Must be a string
        'timezone': 'UTC'
    }

    try:
        response = requests.get(OPEN_METEO_API_URL, params=params)
        if response.status_code != 200:
            logger.error(f"Open-Meteo API returned status code {response.status_code}")
            logger.error(f"Response Content: {response.text}")
            return None
        data = response.json()

        weather_data = {
            'current': {},
            'forecast': []
        }

        # Current weather
        if 'current_weather' in data:
            current = data['current_weather']
            solar_radiation = get_current_solar_radiation(data, current['time'])
            weather_data['current'] = {
                'temperature': current['temperature'],
                'wind_speed': current['windspeed'],
                'wind_direction': current['winddirection'],
                'solar_radiation': solar_radiation
            }

        # Forecast for next 3 days
        daily = data.get('daily', {})
        dates = daily.get('time', [])[:3]
        temp_max = daily.get('temperature_2m_max', [])[:3]
        temp_min = daily.get('temperature_2m_min', [])[:3]
        wind_gusts = daily.get('windspeed_10m_max', [])[:3]
        shortwave_radiation_sum = daily.get('shortwave_radiation_sum', [])[:3]

        for i in range(len(dates)):
            # Calculate average temperature
            if temp_max[i] is not None and temp_min[i] is not None:
                temperature = (temp_max[i] + temp_min[i]) / 2
            else:
                temperature = None

            # Use wind speed max directly
            wind_speed = wind_gusts[i] if wind_gusts[i] is not None else None

            # Extract solar radiation
            solar_radiation = shortwave_radiation_sum[i] if shortwave_radiation_sum[i] is not None else None

            # Short forecast description
            short_forecast = f"Temp: {temp_max[i]}°C max, {temp_min[i]}°C min" if temp_max[i] and temp_min[i] else "No forecast available"

            forecast = {
                'date': dates[i],
                'temperature': temperature,
                'wind_speed': wind_speed,
                'wind_direction': 'Variable',  # Open-Meteo's daily forecast doesn't provide wind direction
                'solar_radiation': solar_radiation,
                'short_forecast': short_forecast
            }
            weather_data['forecast'].append(forecast)

        logger.info("Weather data fetched and parsed successfully.")
        return weather_data

    except Exception as e:
        logger.error(f"Exception while fetching Open-Meteo data: {e}")
        return None

def get_current_solar_radiation(data, current_time_str):
    """
    Extract current solar radiation from hourly data.

    Args:
        data (dict): JSON response from Open-Meteo API.
        current_time_str (str): Current time in ISO format.

    Returns:
        float: Solar radiation value if available, else None.
    """
    try:
        hourly_times = data['hourly']['time']
        solar_radiation = data['hourly']['solar_radiation']
        if current_time_str in hourly_times:
            index = hourly_times.index(current_time_str)
            return solar_radiation[index]
        else:
            logger.warning("Current time not found in hourly solar radiation data.")
            return None
    except Exception as e:
        logger.error(f"Error extracting current solar radiation: {e}")
        return None

def main():
    """
    Main function to execute the weather data retrieval and storage.
    """
    # Configuration
    zip_code = "10001"  # Replace with your desired ZIP code
    db_name = DATABASE_NAME

    # Initialize database
    initialize_database(db_name)

    # Geocode ZIP code
    latitude, longitude = geocode_zip(zip_code)
    if latitude is None or longitude is None:
        logger.error("Geocoding failed. Exiting.")
        return

    # Fetch weather data
    weather_data = fetch_open_meteo_data(latitude, longitude)
    if weather_data is None:
        logger.error("Failed to fetch weather data. Exiting.")
        return

    # Insert current weather
    current = weather_data['current']
    if current:
        insert_current_weather(
            db_name=db_name,
            zip_code=zip_code,
            temperature=current['temperature'],
            wind_speed=current['wind_speed'],
            wind_direction=current['wind_direction'],
            solar_radiation=current['solar_radiation']
        )
    else:
        logger.warning("No current weather data available to insert.")

    # Insert forecast weather
    forecasts = weather_data['forecast']
    if forecasts:
        for forecast in forecasts:
            insert_forecast_weather(
                db_name=db_name,
                zip_code=zip_code,
                date=forecast['date'],
                temperature=forecast['temperature'],
                wind_speed=forecast['wind_speed'],
                wind_direction=forecast['wind_direction'],
                solar_radiation=forecast['solar_radiation'],
                short_forecast=forecast['short_forecast']
            )
    else:
        logger.warning("No forecast weather data available to insert.")

if __name__ == "__main__":
    main()
