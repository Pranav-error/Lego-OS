from flask import Flask, render_template
from flask_socketio import SocketIO
from flask_cors import CORS
import random
import time
import threading

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

def generate_sensor_data():
    """Simulate sensor readings for multiple sensors and emit them via WebSocket."""
    while True:
        data = {
            "UV": random.randint(50, 100),  # UV sensor value
            "Heart Rate": random.randint(60, 120),  # Heart rate in bpm
            "Hydration Level": random.randint(30, 100),  # Hydration level percentage
            "Posture": random.choice(["Good", "Bad"]),  # Posture indicator
            "Blood Pressure": f"{random.randint(90, 140)}/{random.randint(60, 90)} mmHg",  # Systolic/Diastolic
            "Glucose Level": round(random.uniform(70, 140), 2),  # Glucose level (mg/dL)
            "Body Temperature": f"{round(random.uniform(36.0, 38.5), 1)}°C",  # Body temperature in °C
            "Air Quality (Gas Levels)": random.choice(["Good", "Moderate", "Unhealthy", "Hazardous"])  # Air quality
        }
        # Emit the data with an event name matching the one used in the HTML (sensor_update)
        socketio.emit("sensor_update", data)
        time.sleep(2)

if __name__ == '__main__':
    # Start sensor simulation in a separate background thread
    sensor_thread = threading.Thread(target=generate_sensor_data)
    sensor_thread.daemon = True
    sensor_thread.start()

    # Run the Flask app with SocketIO support
    socketio.run(app, debug=True, host='127.0.0.1', port=5000)