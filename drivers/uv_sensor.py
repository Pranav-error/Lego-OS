import time
import random

def run(msg_queue):
    sensor_name = "UV"
    while True:
        value = random.randint(50, 100)
        msg = {"sensor": sensor_name, "value": value}
        msg_queue.put(msg)
        time.sleep(2)
