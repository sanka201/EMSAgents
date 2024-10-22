# weather_forecast_to_sqlite.py

import openmeteo_requests
import requests_cache
from retry_requests import retry
from datetime import datetime, timedelta
import sqlite3
import sys

def get_database_connection(db_name='weather_data.db'):
    """
    Establishes a connection to the SQLite database.

    Args:
        db_name (str): Name of the SQLite database file.

    Returns:
        sqlite3.Connection: SQLite database connection object.
    """
    try:
        conn = sqlite3.connect(db_name)
        return conn
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        sys.exit(1)

def create_tables(conn):
    """
    Creates the necessary tables for minutely and hourly forecasts.
    Drops existing tables to ensure data is overwritten on each run.

    Args:
        conn (sqlite3.Connection): SQLite database connection object.
    """
    try:
        cursor = conn.cursor()
        
        # Drop existing tables if they exist
        cursor.execute("DROP TABLE IF EXISTS minutely_forecast;")
        cursor.execute("DROP TABLE IF EXISTS hourly_forecast;")
        
        # Create minutely_forecast table
        cursor.execute("""
            CREATE TABLE minutely_forecast (
                time TEXT PRIMARY KEY,
                temperature_2m REAL,
                apparent_temperature REAL,
                wind_speed_10m REAL,
                wind_gusts_10m REAL,
                direct_radiation REAL,
                diffuse_radiation REAL,
                direct_normal_irradiance REAL,
                shortwave_radiation_instant REAL,
                direct_radiation_instant REAL,
                diffuse_radiation_instant REAL,
                direct_normal_irradiance_instant REAL
            );
        """)
        
        # Create hourly_forecast table
        cursor.execute("""
            CREATE TABLE hourly_forecast (
                time TEXT PRIMARY KEY,
                temperature_2m REAL,
                cloud_cover REAL,
                cloud_cover_low REAL,
                cloud_cover_mid REAL,
                cloud_cover_high REAL,
                wind_speed_10m REAL,
                wind_direction_10m REAL,
                wind_gusts_10m REAL,
                shortwave_radiation REAL,
                direct_radiation REAL,
                diffuse_radiation REAL,
                direct_normal_irradiance REAL,
                shortwave_radiation_instant REAL,
                direct_radiation_instant REAL,
                diffuse_radiation_instant REAL,
                direct_normal_irradiance_instant REAL
            );
        """)
        
        conn.commit()
        print("Database tables created successfully.")
    except sqlite3.Error as e:
        print(f"SQLite error during table creation: {e}")
        conn.rollback()
        sys.exit(1)

def insert_minutely_data(conn, minutely_data):
    """
    Inserts minutely forecast data into the minutely_forecast table.

    Args:
        conn (sqlite3.Connection): SQLite database connection object.
        minutely_data (list of dict): List containing minutely forecast data dictionaries.
    """
    try:
        cursor = conn.cursor()
        for entry in minutely_data:
            cursor.execute("""
                INSERT INTO minutely_forecast (
                    time,
                    temperature_2m,
                    apparent_temperature,
                    wind_speed_10m,
                    wind_gusts_10m,
                    direct_radiation,
                    diffuse_radiation,
                    direct_normal_irradiance,
                    shortwave_radiation_instant,
                    direct_radiation_instant,
                    diffuse_radiation_instant,
                    direct_normal_irradiance_instant
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                entry['time'],
                entry.get('temperature_2m'),
                entry.get('apparent_temperature'),
                entry.get('wind_speed_10m'),
                entry.get('wind_gusts_10m'),
                entry.get('direct_radiation'),
                entry.get('diffuse_radiation'),
                entry.get('direct_normal_irradiance'),
                entry.get('shortwave_radiation_instant'),
                entry.get('direct_radiation_instant'),
                entry.get('diffuse_radiation_instant'),
                entry.get('direct_normal_irradiance_instant')
            ))
        conn.commit()
        print(f"Inserted {len(minutely_data)} records into minutely_forecast table.")
    except sqlite3.Error as e:
        print(f"SQLite error during minutely data insertion: {e}")
        conn.rollback()
        sys.exit(1)

def insert_hourly_data(conn, hourly_data):
    """
    Inserts hourly forecast data into the hourly_forecast table.

    Args:
        conn (sqlite3.Connection): SQLite database connection object.
        hourly_data (list of dict): List containing hourly forecast data dictionaries.
    """
    try:
        cursor = conn.cursor()
        for entry in hourly_data:
            cursor.execute("""
                INSERT INTO hourly_forecast (
                    time,
                    temperature_2m,
                    cloud_cover,
                    cloud_cover_low,
                    cloud_cover_mid,
                    cloud_cover_high,
                    wind_speed_10m,
                    wind_direction_10m,
                    wind_gusts_10m,
                    shortwave_radiation,
                    direct_radiation,
                    diffuse_radiation,
                    direct_normal_irradiance,
                    shortwave_radiation_instant,
                    direct_radiation_instant,
                    diffuse_radiation_instant,
                    direct_normal_irradiance_instant
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                entry['time'],
                entry.get('temperature_2m'),
                entry.get('cloud_cover'),
                entry.get('cloud_cover_low'),
                entry.get('cloud_cover_mid'),
                entry.get('cloud_cover_high'),
                entry.get('wind_speed_10m'),
                entry.get('wind_direction_10m'),
                entry.get('wind_gusts_10m'),
                entry.get('shortwave_radiation'),
                entry.get('direct_radiation'),
                entry.get('diffuse_radiation'),
                entry.get('direct_normal_irradiance'),
                entry.get('shortwave_radiation_instant'),
                entry.get('direct_radiation_instant'),
                entry.get('diffuse_radiation_instant'),
                entry.get('direct_normal_irradiance_instant')
            ))
        conn.commit()
        print(f"Inserted {len(hourly_data)} records into hourly_forecast table.")
    except sqlite3.Error as e:
        print(f"SQLite error during hourly data insertion: {e}")
        conn.rollback()
        sys.exit(1)

def fetch_and_store_weather():
    """
    Fetches weather data from Open-Meteo API and stores it into SQLite database.
    """
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    
    # Define API parameters
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 33.6036,
        "longitude": -101.969,
        "minutely_15": [
            "temperature_2m", "apparent_temperature", "wind_speed_10m",
            "wind_gusts_10m", "direct_radiation", "diffuse_radiation",
            "direct_normal_irradiance", "shortwave_radiation_instant",
            "direct_radiation_instant", "diffuse_radiation_instant",
            "direct_normal_irradiance_instant"
        ],
        "hourly": [
            "temperature_2m", "cloud_cover", "cloud_cover_low",
            "cloud_cover_mid", "cloud_cover_high", "wind_speed_10m",
            "wind_direction_10m", "wind_gusts_10m", "shortwave_radiation",
            "direct_radiation", "diffuse_radiation",
            "direct_normal_irradiance", "shortwave_radiation_instant",
            "direct_radiation_instant", "diffuse_radiation_instant",
            "direct_normal_irradiance_instant"
        ],
        "wind_speed_unit": "mph",
        "timezone": "GMT",
        "forecast_days": 3
    }
    
    # Fetch weather data
    try:
        responses = openmeteo.weather_api(url, params=params)
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        sys.exit(1)
    
    if not responses:
        print("No responses received from Open-Meteo API.")
        sys.exit(1)
    
    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation {response.Elevation()} m asl")
    print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
    print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")
    
    # Process minutely_15 data
    minutely_15 = response.Minutely15()
    minutely_15_time_start = datetime.utcfromtimestamp(minutely_15.Time())
    minutely_15_time_end = datetime.utcfromtimestamp(minutely_15.TimeEnd())
    minutely_15_interval = minutely_15.Interval()  # in seconds
    
    minutely_15_data = []
    current_time = minutely_15_time_start
    num_minutely_entries = len(minutely_15.Variables(0).ValuesAsNumpy())  # Corrected line
    
    for i in range(num_minutely_entries):
        minutely_15_data.append({
            "time": current_time.strftime("%Y-%m-%d %H:%M"),
            "temperature_2m": minutely_15.Variables(0).ValuesAsNumpy()[i],
            "apparent_temperature": minutely_15.Variables(1).ValuesAsNumpy()[i],
            "wind_speed_10m": minutely_15.Variables(2).ValuesAsNumpy()[i],
            "wind_gusts_10m": minutely_15.Variables(3).ValuesAsNumpy()[i],
            "direct_radiation": minutely_15.Variables(4).ValuesAsNumpy()[i],
            "diffuse_radiation": minutely_15.Variables(5).ValuesAsNumpy()[i],
            "direct_normal_irradiance": minutely_15.Variables(6).ValuesAsNumpy()[i],
            "shortwave_radiation_instant": minutely_15.Variables(7).ValuesAsNumpy()[i],
            "direct_radiation_instant": minutely_15.Variables(8).ValuesAsNumpy()[i],
            "diffuse_radiation_instant": minutely_15.Variables(9).ValuesAsNumpy()[i],
            "direct_normal_irradiance_instant": minutely_15.Variables(10).ValuesAsNumpy()[i]
        })
        current_time += timedelta(seconds=minutely_15_interval)
    
    # Process hourly data
    hourly = response.Hourly()
    hourly_time_start = datetime.utcfromtimestamp(hourly.Time())
    hourly_time_end = datetime.utcfromtimestamp(hourly.TimeEnd())
    hourly_interval = hourly.Interval()  # in seconds
    
    hourly_data = []
    current_time = hourly_time_start
    num_hourly_entries = len(hourly.Variables(0).ValuesAsNumpy())  # Corrected line
    
    for i in range(num_hourly_entries):
        hourly_data.append({
            "time": current_time.strftime("%Y-%m-%d %H:%M"),
            "temperature_2m": hourly.Variables(0).ValuesAsNumpy()[i],
            "cloud_cover": hourly.Variables(1).ValuesAsNumpy()[i],
            "cloud_cover_low": hourly.Variables(2).ValuesAsNumpy()[i],
            "cloud_cover_mid": hourly.Variables(3).ValuesAsNumpy()[i],
            "cloud_cover_high": hourly.Variables(4).ValuesAsNumpy()[i],
            "wind_speed_10m": hourly.Variables(5).ValuesAsNumpy()[i],
            "wind_direction_10m": hourly.Variables(6).ValuesAsNumpy()[i],
            "wind_gusts_10m": hourly.Variables(7).ValuesAsNumpy()[i],
            "shortwave_radiation": hourly.Variables(8).ValuesAsNumpy()[i],
            "direct_radiation": hourly.Variables(9).ValuesAsNumpy()[i],
            "diffuse_radiation": hourly.Variables(10).ValuesAsNumpy()[i],
            "direct_normal_irradiance": hourly.Variables(11).ValuesAsNumpy()[i],
            "shortwave_radiation_instant": hourly.Variables(12).ValuesAsNumpy()[i],
            "direct_radiation_instant": hourly.Variables(13).ValuesAsNumpy()[i],
            "diffuse_radiation_instant": hourly.Variables(14).ValuesAsNumpy()[i],
            "direct_normal_irradiance_instant": hourly.Variables(15).ValuesAsNumpy()[i]
        })
        current_time += timedelta(seconds=hourly_interval)
    
    # Connect to SQLite database
    conn = get_database_connection()
    
    # Create tables
    create_tables(conn)
    
    # Insert data into tables
    insert_minutely_data(conn, minutely_15_data)
    insert_hourly_data(conn, hourly_data)
    
    # Close the database connection
    conn.close()
    print("Weather data has been successfully saved to the SQLite database.")

def main():
    """
    Main function to orchestrate fetching and storing weather data.
    """
    fetch_and_store_weather()

if __name__ == "__main__":
    main()
