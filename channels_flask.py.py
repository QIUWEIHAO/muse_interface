from flask import Flask, render_template_string
from pylsl import resolve_stream
import threading
import time

app = Flask(__name__)

# Shared data structure to store streams
streams_status = {}

# Mapping of Source IDs to device names
SOURCE_IDs = {
    'Muse00:55:DA:B8:05:30': 'Muse-0530',
    'Muse00:55:DA:B6:00:AC': 'Muse-00AC',
    'Muse00:55:DA:B7:EB:8D': 'Muse-EB8D',
    'Muse00:55:DA:B5:EF:CD': 'Muse-EFCD',
    'Muse00:55:DA:B6:00:AD': 'Muse-00AD',
    'Muse00:55:DA:B6:07:9C': 'Muse-079C',
    'Muse143648F2-D9AD-77CC-5E6D-4C6185E433A9': 'Muse-00AC',
    'Muse6CAEA77C-CFB5-8297-B709-419565E920D1': 'Muse-0530',
    'MuseFCC7CA7F-9A94-727A-621C-09620A24A809': 'Muse-EFCD',
    'MuseA6F24BE5-6134-D1E5-2A8D-96F242EC5448': 'Muse-EB8D',
    'MuseAAAD869F-7E03-A2DA-5BC5-05D1CFAB4373': 'Muse-00AD',
    'Muse68F92D62-07FF-DC68-09E6-ED2A18DD5EAB': 'Muse-079C',
}

# Predefined list of all device names
ALL_DEVICES = [
    "Muse-0530",
    "Muse-00AC",
    "Muse-EB8D",
    "Muse-EFCD",
    "Muse-00AD",
    "Muse-079C",
]

# HTML template for visualization
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Muse Devices Availability</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .container {
            padding-left: 0;
        }
        .signal-row {
            display: flex;
            align-items: center;
            margin-left: 0;
        }
        .signal-box {
            width: 100px;
            height: 40px;
            display: flex;
            justify-content: center;
            align-items: center;
            border: 1px solid #ddd;
            text-align: center;
            font-size: 12px;
            font-weight: bold;
            color: white;
            margin-right: 5px;
            border-radius: 5px;
        }
        .green { background-color: green; }
        .grey { background-color: grey; }
        .device-header {
            font-weight: bold;
            text-align: left;
            margin-bottom: 5px;
            margin-left: 0;
        }
        .device-row {
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container mt-3">
        <h1 class="text-left mb-4">Muse Devices Availability</h1>
        <div class="row">
            {% for index, device_name in enumerate(devices) %}
            <div class="col-12 device-row">
                <!-- Device Header -->
                <div class="device-header">
                    {{ '%02d' % (index + 1) }} {{ device_name }}
                </div>
                <!-- Signal Indicators -->
                <div class="signal-row">
                    {% for signal in ['EEG', 'GYRO', 'PPG', 'ACC'] %}
                    <div class="signal-box {% if streams[device_name][signal] %}green{% else %}grey{% endif %}">
                        {{ signal }}
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

# Background thread to periodically update stream data
def update_streams():
    global streams_status
    while True:
        # Reset streams status for all devices
        streams_status = {device: {"EEG": False, "GYRO": False, "PPG": False, "ACC": False} for device in ALL_DEVICES}

        # Resolve all streams
        resolved_streams = resolve_stream()

        # Map streams to devices
        for stream in resolved_streams:
            source_id = stream.source_id() if hasattr(stream, "source_id") else None
            device_name = SOURCE_IDs.get(source_id, None)
            if device_name and device_name in streams_status:
                stream_type = stream.type()
                if stream_type in streams_status[device_name]:
                    streams_status[device_name][stream_type] = True

        time.sleep(2)  # Update every 2 seconds

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, devices=ALL_DEVICES, streams=streams_status, enumerate=enumerate)

if __name__ == "__main__":
    # Start the background thread
    thread = threading.Thread(target=update_streams, daemon=True)
    thread.start()

    # Run the Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)
