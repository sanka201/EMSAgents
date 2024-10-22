import requests
import websocket

# Get the list of all open tabs
response = requests.get('http://192.168.129.180:10500/json')
tabs = response.json()

# Connect to the WebSocket of the desired tab
ws = websocket.create_connection(tabs[0]['webSocketDebuggerUrl'])

# Send commands via DevTools Protocol to retrieve data
ws.send('{"id": 1, "method": "Runtime.evaluate", "params": {"expression": "document.body.innerHTML"}}')
result = ws.recv()
print(result)

ws.close()
