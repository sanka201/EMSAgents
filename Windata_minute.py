import sqlite3
import openmeteo_requests
import requests_cache
import pandas as pd
import numpy as np
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def setup_openmeteo_client():
    # Setup Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_strategy = Retry(
        total=5,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=0.2
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    cache_session.mount("https://", adapter)
    return openmeteo_requests.Client(session=cache_session)

def fetch_weather_data(client):
    # Define API parameters
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 33.6036,
        "longitude": -101.969,
        "minutely_15": [
            "temperature_2m", "apparent_temperature", "wind_speed_10m", "wind_gusts_10m",
            "direct_radiation", "diffuse_radiation", "direct_normal_irradiance", "shortwave_radiation_instant",
            "direct_radiation_instant", "diffuse_radiation_instant", "direct_normal_irradiance_instant"
        ],
        "hourly": [
            "temperature_2m", "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high",
            "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "shortwave_radiation", "direct_radiation",
            "diffuse_radiation", "direct_normal_irradiance", "shortwave_radiation_instant",
            "direct_radiation_instant", "diffuse_radiation_instant", "direct_normal_irradiance_instant"
        ],
        "wind_speed_unit": "mph",
        "timezone": "GMT",
        "forecast_days": 3
    }
    responses = client.weather_api(url, params=params)
    return responses[0]

def process_minutely_15_data(minutely_15):
    minutely_15_data = {
        "date": pd.date_range(
            start=pd.to_datetime(minutely_15.Time(), unit="s", utc=True),
            end=pd.to_datetime(minutely_15.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=minutely_15.Interval()),
            inclusive="left"
        )
    }
    # Add all variables to dictionary
    for i, variable_name in enumerate([
        "temperature_2m", "apparent_temperature", "wind_speed_10m", "wind_gusts_10m", "direct_radiation",
        "diffuse_radiation", "direct_normal_irradiance", "shortwave_radiation_instant", "direct_radiation_instant",
        "diffuse_radiation_instant", "direct_normal_irradiance_instant"]):
        minutely_15_data[variable_name] = minutely_15.Variables(i).ValuesAsNumpy()

    # Convert wind speed from mph to m/s
    wind_speed_mph = minutely_15_data["wind_speed_10m"]
    wind_speed_ms = wind_speed_mph * 0.44704

    # Calculate predicted wind power output using power curve for 10 kW Bergey wind turbine
    minutely_15_data["predicted_wind_output_kw"] = calculate_wind_power_output(wind_speed_ms)

    return pd.DataFrame(data=minutely_15_data)

def process_hourly_data(hourly):
    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        )
    }
    # Add all variables to dictionary
    for i, variable_name in enumerate([
        "temperature_2m", "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high",
        "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "shortwave_radiation", "direct_radiation",
        "diffuse_radiation", "direct_normal_irradiance", "shortwave_radiation_instant", "direct_radiation_instant",
        "diffuse_radiation_instant", "direct_normal_irradiance_instant"]):
        hourly_data[variable_name] = hourly.Variables(i).ValuesAsNumpy()

    # Convert wind speed from mph to m/s
    wind_speed_mph = hourly_data["wind_speed_10m"]
    wind_speed_ms = wind_speed_mph * 0.44704

    # Calculate predicted wind power output using power curve for 10 kW Bergey wind turbine
    hourly_data["predicted_wind_output_kw"] = calculate_wind_power_output(wind_speed_ms)

    return pd.DataFrame(data=hourly_data)

def calculate_wind_power_output(wind_speed):
    # Power curve for 10 kW Bergey wind turbine
    power_curve = {
        1: 0.00, 2: 0.00, 3: 0.10, 4: 0.40, 5: 0.85,
        6: 1.51, 7: 2.40, 8: 3.60, 9: 5.07, 10: 6.86,
        11: 8.86, 12: 10.88, 13: 12.09, 14: 12.39, 15: 12.49,
        16: 12.55, 17: 12.50, 18: 12.44, 19: 12.21, 20: 11.99
    }
    power_output = []
    for speed in wind_speed:
        speed_bin = min(int(speed), max(power_curve.keys()))
        power_output.append(power_curve.get(speed_bin, 0.0))
    return np.array(power_output)

def create_database_if_not_exists(database_name):
    with sqlite3.connect(database_name) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS minutely_15 (date TEXT PRIMARY KEY)")
        cursor.execute("CREATE TABLE IF NOT EXISTS hourly (date TEXT PRIMARY KEY)")

def save_to_sqlite(database_name, table_name, dataframe):
    create_database_if_not_exists(database_name)
    with sqlite3.connect(database_name) as conn:
        dataframe.to_sql(table_name, conn, if_exists='replace', index=False)

def retrieve_data_from_sqlite(database_name, table_name):
    with sqlite3.connect(database_name) as conn:
        query = f"SELECT * FROM {table_name}"
        dataframe = pd.read_sql_query(query, conn)
    return dataframe

def main():
    # Setup client and fetch data
    openmeteo_client = setup_openmeteo_client()
    response = fetch_weather_data(openmeteo_client)

    # Process minutely_15 and hourly data
    minutely_15_dataframe = process_minutely_15_data(response.Minutely15())
    hourly_dataframe = process_hourly_data(response.Hourly())

    # Save data to SQLite database
    save_to_sqlite("weather_data.db", "minutely_15", minutely_15_dataframe)
    save_to_sqlite("weather_data.db", "hourly", hourly_dataframe)

if __name__ == "__main__":
    main()