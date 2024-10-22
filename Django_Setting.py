# List of topics to be watched. Messages received will be written to stdout.
topic_prefixes_to_watch = ['']
# Seconds between hearbeat publishes
heartbeat_period = 10

# Volttron address and keys used to create agents
agent_kwargs = {
    # Volttron VIP address
    'address': 'tcp://192.168.10.254:22916',

    # Required keys for establishing an encrypted VIP connection
    'secretkey': 'QGVtLrRcC7JUfoJU1A-Mf4dlfzBfzD_Ac6yL3zYBQ7M',
    'publickey': '_jrGYZ09FOVgv7wMit7lH2rOBFlF0FoojFHf4MuG_H8',
    'serverkey': 'PAyMf9eTKxFKDTbeWfxx4TsZPYpmNA3j1FjwLoBPVws',
}
