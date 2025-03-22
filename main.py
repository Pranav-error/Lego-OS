import threading
import queue
import time
import importlib

# Define a simple microkernel
class MicroKernel:
    def __init__(self):
        self.message_queue = queue.Queue()
        self.running = True
        self.drivers = {}

    def start(self):
        print("Kernel starting...")
        threading.Thread(target=self.kernel_loop, daemon=True).start()

    def kernel_loop(self):
        print("[Kernel] Running main loop...")  # ✅ FIXED INDENTATION
        while self.running:
            try:
                message = self.message_queue.get(timeout=1)
                print(f"[Kernel] Received: {message}")
                self.process_message(message)
            except queue.Empty:
                print("[Kernel] No messages yet...")

    def process_message(self, message):
        sensor = message.get("sensor")
        value = message.get("value")
        print(f"[Kernel] Processing data from {sensor}: {value}")

        if sensor == "UV" and value > 70:
            print("[Kernel] Alert: High UV detected! Seek shade!")

    def load_driver(self, driver_name):
        try:
            module = importlib.import_module(f"drivers.{driver_name}")
            driver_thread = threading.Thread(target=module.run, args=(self.message_queue,), daemon=True)
            driver_thread.start()
            self.drivers[driver_name] = driver_thread
            print(f"[Kernel] Driver '{driver_name}' loaded.")
        except Exception as e:
            print(f"[Kernel] Failed to load driver {driver_name}: {e}")

    def stop(self):
        self.running = False
        print("Kernel shutting down...")

if __name__ == "__main__":
    kernel = MicroKernel()
    kernel.start()

    # Load drivers dynamically
    kernel.load_driver("uv_sensor")
    kernel.load_driver("heart_rate")

    try:
        time.sleep(20)
    except KeyboardInterrupt:
        pass
    finally:
        kernel.stop()
