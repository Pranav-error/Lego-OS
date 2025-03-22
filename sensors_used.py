import time
import random
import json

def run(msg_queue):
    sensor_name = "Blood Pressure"
    while True:
        systolic = random.randint(90, 140)  # Systolic Pressure
        diastolic = random.randint(60, 90)  # Diastolic Pressure
        
        # Create a structured JSON object
        msg = {
            "sensor": sensor_name,
            "systolic": systolic,
            "diastolic": diastolic,
            "unit": "mmHg",
            "value": f"{systolic}/{diastolic} mmHg"
        }

        # Convert to JSON string before putting in queue (optional)
        json_msg = json.dumps(msg)

        msg_queue.put(json_msg)
        time.sleep(2)

def run(msg_queue):
    sensor_name = "Body Temperature"
    while True:
        value = round(random.uniform(36.0, 38.5), 1)  # Simulating body temperature (°C)
        msg = {"sensor": sensor_name, "value": f"{value}°C"}
        msg_queue.put(msg)
        time.sleep(2)


def run(msg_queue):
    sensor_name = "Air Quality (Gas Levels)"
    gases = ["Good", "Moderate", "Unhealthy", "Hazardous"]
    while True:
        value = random.choice(gases)  # Simulating air quality
        msg = {"sensor": sensor_name, "value": value}
        msg_queue.put(msg)
        time.sleep(2)

        
def run(msg_queue):
    sensor_name = "Glucose Level"
    while True:
        value = random.uniform(70, 140)  # Simulating glucose levels (mg/dL)
        msg = {"sensor": sensor_name, "value": round(value, 2)}
        msg_queue.put(msg)
        time.sleep(2)
