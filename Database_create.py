import sqlite3

# Connect to the SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('./FacadeAgent/Device_configure_database.sqlite')

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

# Create the Buildings table
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS buildings (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT NOT NULL,
#     address TEXT
# )
# ''')

# # Create the Controllers table
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS controllers (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT NOT NULL,
#     building_id INTEGER,
#     FOREIGN KEY (building_id) REFERENCES buildings(id)
# )
# ''')

# Create the Devices table
cursor.execute('''
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT NOT NULL UNIQUE,
    max_power_rating REAL NOT NULL,
    controller_id TEXT,
    building_id TEXT,
    priority INT NOT NULL,
    power_multiply_factor FLOAT
)
''')

# Commit the changes
conn.commit()

# Close the connection
conn.close()

print("Database and tables created successfully.")
