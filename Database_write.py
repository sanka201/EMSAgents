import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('./FacadeAgent/Device_configure_database.sqlite')

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

# Function to insert a new device into the devices table
def insert_device(device_id, max_power_rating, controller_id=None,building_id=None, priority=0,mutlipy_factor=1):
    try:
        cursor.execute('''
            INSERT INTO devices (device_id, max_power_rating, controller_id,building_id,priority,power_multiply_factor)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (device_id, max_power_rating, controller_id,building_id,priority,mutlipy_factor))
        conn.commit()
        print(f"Device {device_id} inserted successfully.")
    except sqlite3.IntegrityError:
        print(f"Error: Device with ID {device_id} already exists.")

# Function to update an existing device in the devices table
def update_device(device_id, max_power_rating=None, controller_id=None,building_id=None,priority=0,mutlipy_factor=1):
    # Build the SQL update query dynamically based on the provided fields
    update_query = "UPDATE devices SET "
    update_fields = []
    update_values = []
    
    if max_power_rating is not None:
        update_fields.append("max_power_rating = ?")
        update_values.append(max_power_rating)
    
    if controller_id is not None:
        update_fields.append("controller_id = ?")
        update_values.append(controller_id)
    if building_id is not None:
        update_fields.append("building_id = ?")
        update_values.append(building_id)
        
    if priority is not None:
        update_fields.append("priority = ?")
        update_values.append(priority)
        
    if mutlipy_factor is not None:
        update_fields.append("power_multiply_factor = ?")
        update_values.append(mutlipy_factor)
    
    if not update_fields:
        print(f"No fields provided for update for device {device_id}.")
        return
    
    update_query += ", ".join(update_fields)
    update_query += " WHERE device_id = ?"
    update_values.append(device_id)
    
    cursor.execute(update_query, update_values)
    conn.commit()
    print(f"Device {device_id} updated successfully.")

# Example usage:
p=[1,2,1,1,3,2,2,2,1,1,3,1,1,1,3,3,3,2,2,1,1,3,1]
for i in range(0,15):
    insert_device('building540/NIRE_WeMo_cc_1/w'+str(i+1), 5.0, 'NIRE_WeMo_cc_1','building540',p[i],0.001)


for j in range(0,11):
    print(j)
    insert_device('building540/NIRE_WeMo_cc_4/w'+str(j+1), 5.0, 'NIRE_WeMo_cc_4','building540',p[j],0.001)

    
for j in range(0,14):
    print(j)
    insert_device('building540/NIRE_ALPHA_cc_2/w'+str(j+1), 5.0, 'NIRE_ALPHA_cc_2','building540',p[j],0.001)
    
insert_device('building540/NIRE_ALPHA_cc_1/w2', 5.0, 'NIRE_ALPHA_cc_1','building540',1)
insert_device('building540/NIRE_ALPHA_cc_1/w3', 5.0, 'NIRE_ALPHA_cc_1','building540',1)
insert_device('building540/NIRE_ALPHA_cc_1/w4', 5.0, 'NIRE_ALPHA_cc_1','building540',1)
insert_device('building540/NIRE_ALPHA_cc_1/w6', 5.0, 'NIRE_ALPHA_cc_1','building540',2)
insert_device('building540/NIRE_ALPHA_cc_1/w17', 5.0, 'NIRE_ALPHA_cc_1','building540',3)
insert_device('building540/NIRE_ALPHA_cc_1/w19', 5.0, 'NIRE_ALPHA_cc_1','building540',3)


# update_device('w1', max_power_rating=175.0)
# update_device('w2', controller_id='Alpha_CC_1')
# update_device('w1', max_power_rating=180.0,building_id='GLEAMM')

# Close the connection
conn.close()
