import asyncio
import websockets
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import Action, RegistrationStatus
from ocpp.routing import on

class ChargePoint(cp):
    @on(Action.BootNotification)
    async def on_boot_notification(self, charge_point_model, charge_point_vendor, **kwargs):
        # Respond to boot notification with status Accepted
        return {
            "status": RegistrationStatus.accepted,
            "current_time": "2023-01-01T00:00:00Z",
            "interval": 10
        }

async def connect_to_ev_charger():
    # Define the WebSocket URL of the charger
    charger_ip = "192.168.129.152"
    port = 80  # Standard port for OCPP; verify with your charger
    ws_url = f"ws://{charger_ip}:{port}/ocpp/"

    # Define an identifier for the charge point
    charge_point_id = "EV_Charger_001"

    async with websockets.connect(ws_url, subprotocols=['ocpp1.6']) as websocket:
        # Create ChargePoint instance
        charge_point = ChargePoint(charge_point_id, websocket)
        
        # Start listening for OCPP messages
        await charge_point.start()

# Run the async function
asyncio.run(connect_to_ev_charger())
