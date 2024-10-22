import sqlite3

import pandas as pd


def retrieve_data_from_sqlite(database_name, table_name):
    with sqlite3.connect(database_name) as conn:
        query = f"SELECT * FROM {table_name}"
        dataframe = pd.read_sql_query(query, conn)
    return dataframe

def main():


    # Retrieve data from SQLite database
    retrieved_minutely_15 = retrieve_data_from_sqlite("weather_data.db", "minutely_15")
    retrieved_hourly = retrieve_data_from_sqlite("weather_data.db", "hourly")
    pd.set_option('display.max_rows', None)
    # Print retrieved dataframes
    print(retrieved_minutely_15.head(160))
    print(retrieved_hourly)

if __name__ == "__main__":
    main()