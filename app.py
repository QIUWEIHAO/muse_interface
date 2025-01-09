from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from pythonosc import udp_client
import threading
import asyncio
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
import time

app = Flask(__name__)
socketio = SocketIO(app)

# OSC Client for sending control commands
osc_client = udp_client.SimpleUDPClient("127.0.0.1", 5005)

# Example muse device data
muse_data = {
    "Muse-0530": {"status": "off", "signalquality": [0, 0, 0, 0]},
    "Muse-00AC": {"status": "off", "signalquality": [0, 0, 0, 0]},
    "Muse-EB8D": {"status": "off", "signalquality": [0, 0, 0, 0]},
    "Muse-EFCD": {"status": "off", "signalquality": [0, 0, 0, 0]},
    "Muse-00AD": {"status": "off", "signalquality": [0, 0, 0, 0]},
    "Muse-079C": {"status": "off", "signalquality": [0, 0, 0, 0]},
    "Muse-DD90": {"status": "off", "signalquality": [0, 0, 0, 0]}
    # Add other muse devices here
}

data_lock = threading.Lock()

# Function to reset all values in muse_data
def reset_muse_data():
    global muse_data
    while True:
        time.sleep(4)  # Reset every 60 seconds (adjust as needed)
        with data_lock:
            for muse in muse_data.values():
                muse["status"] = "off"
                muse["signalquality"] = [0, 0, 0, 0]
            # print("Muse data has been reset:", muse_data)
            # Emit the updated muse_data to all connected clients
            # socketio.emit("muse_data_update", muse_data)



PORT = 7656  # Port to listen on
def osc_listener():
    """Listen for OSC messages from TouchDesigner."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Define the dispatcher to handle incoming OSC messages
    dispatcher = Dispatcher()

    # Map OSC addresses to functions
    dispatcher.map("/Muse-*/eeg-*", update_signal_quality)  # Matches EEG signal paths
    dispatcher.map("/*", print_osc_message)  # Fallback for debugging other OSC messages

    # Create and start the OSC server
    server = AsyncIOOSCUDPServer(("localhost", PORT), dispatcher, loop)
    print(f"Listening for OSC messages on localhost:{PORT}")
    loop.run_until_complete(server.create_serve_endpoint())
    loop.run_forever()

def update_signal_quality(address, *args):
    global muse_data 
    """Update signal quality in the muse_data dictionary."""
    # Extract device name and signal type from the OSC address
    parts = address.split('/')
    device_name = parts[1]  # E.g., "Muse-00AC"
    signal_type = parts[2]  # E.g., "eeg-tp9-le"

    # Map signal types to indices
    signal_mapping = {
        "eeg-tp9-le": 0,
        "eeg-af7-lf": 1,
        "eeg-af8-rf": 2,
        "eeg-tp10-re": 3,
    }

    # Update signal quality if device is in muse_data
    if device_name in muse_data and signal_type in signal_mapping:
        index = signal_mapping[signal_type]
        # Use the first value from args to determine signal quality (1.0 -> 1, 0.0 -> 0)
        with data_lock:
            muse_data[device_name]["status"] = 'on'
            muse_data[device_name]["signalquality"][index] = int(args[0] > 0)

            # Emit updated muse_data to all clients
            # socketio.emit('muse_data_update', muse_data)

def print_osc_message(address, *args):
    """Print received OSC messages."""
    # print(f"Received OSC message: Address: {address}, Arguments: {args}")
    return

@app.route('/')
def index():
    # print(muse_data)
    return render_template("index.html", muse_data = muse_data)

@socketio.on('send_command')
def handle_command(data):
    """Handle button/toggle events."""
    print("Received data:", data)  # Debugging
    command = data.get("command")
    value = data.get("value", None)
    print("Parsed command:", command, "Value:", value)  # Debugging

    if value is not None:
        osc_client.send_message(command, value)
        print(f"OSC Sent -> Command: {command}, Value: {value}")
    else:
        osc_client.send_message(command, [])
        print(f"OSC Sent -> Command: {command}")

    emit("command_sent", {"status": "success"}, broadcast=True)

# Endpoint to serve muse data as JSON
@app.route("/muse-data")
def get_muse_data():
    with data_lock:
        # print(muse_data)
        socketio.emit('muse_data_update', muse_data)
    return jsonify(muse_data)


if __name__ == "__main__":
    thread = threading.Thread(target=osc_listener, daemon=True)
    thread.start()
    # Start the reset function in a separate thread
    reset_thread = threading.Thread(target=reset_muse_data, daemon=True)
    reset_thread.start()
    socketio.run(app, host = '0.0.0.0', debug=True)
