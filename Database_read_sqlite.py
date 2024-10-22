import sqlite3

# Step 1: Connect to the SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('./FacadeAgent/Device_configure_database.sqlite')

# Step 2: Create a cursor object
cursor = conn.cursor()

# Step 3: Execute a SELECT query
cursor.execute("SELECT * FROM devices")

# Step 4: Fetch the results
rows = cursor.fetchall()  # To fetch all rows
# rows = cursor.fetchone()  # To fetch the first row
# rows = cursor.fetchmany(10)  # To fetch the first 10 rows

# Step 5: Work with the fetched data
for row in rows:
    print(row)

# Step 6: Close the cursor and connection
cursor.close()
conn.close()