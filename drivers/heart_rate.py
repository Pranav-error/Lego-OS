import time
import random

def run(msg_queue):
    sensor_name = "Heart Rate"
    while True:
        value = random.randint(60, 120)  # Simulating a normal heart rate range
        msg = {"sensor": sensor_name, "value": value}
        msg_queue.put(msg)
        time.sleep(2)
