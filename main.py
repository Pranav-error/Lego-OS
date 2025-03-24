import threading
import queue
import time
import importlib
import logging
import uuid
from typing import Dict, List, Any, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class Process:
    """Represents a process in the microkernel system"""
    
    def __init__(self, pid: str, name: str, target: Callable, args=(), kwargs={}):
        self.pid = pid
        self.name = name
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.thread = None
        self.running = False
        self.message_queue = queue.Queue()
        
    def start(self):
        """Start the process thread"""
        self.running = True
        self.thread = threading.Thread(
            target=self._run_wrapper,
            daemon=True
        )
        self.thread.start()
        
    def _run_wrapper(self):
        """Wrapper to handle exceptions and process termination"""
        try:
            self.target(self, *self.args, **self.kwargs)
        except Exception as e:
            logging.error(f"Process {self.name} (PID: {self.pid}) crashed: {e}")
        finally:
            self.running = False
            
    def send_message(self, message: Dict[str, Any]):
        """Add a message to this process's queue"""
        self.message_queue.put(message)
        
    def receive_message(self, timeout=None):
        """Get a message from this process's queue"""
        try:
            return self.message_queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def terminate(self):
        """Terminate the process"""
        self.running = False
        # Cannot directly terminate a thread in Python,
        # but we can set a flag that the process should check

class Service:
    """Base class for all microkernel services"""
    
    def __init__(self, name: str):
        self.name = name
        self.kernel = None
        
    def initialize(self, kernel):
        """Initialize the service with a reference to the kernel"""
        self.kernel = kernel
        
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message sent to this service"""
        raise NotImplementedError("Service must implement process_message")

class FileSystemService(Service):
    """A simple in-memory file system service"""
    
    def __init__(self):
        super().__init__("filesystem")
        self.files = {}
        
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        operation = message.get("operation")
        
        if operation == "write":
            path = message.get("path")
            content = message.get("content")
            self.files[path] = content
            return {"status": "success", "operation": "write", "path": path}
            
        elif operation == "read":
            path = message.get("path")
            if path in self.files:
                return {
                    "status": "success", 
                    "operation": "read", 
                    "path": path, 
                    "content": self.files[path]
                }
            else:
                return {
                    "status": "error", 
                    "operation": "read", 
                    "path": path, 
                    "error": "File not found"
                }
                
        elif operation == "list":
            return {
                "status": "success", 
                "operation": "list", 
                "files": list(self.files.keys())
            }
            
        else:
            return {
                "status": "error", 
                "operation": operation, 
                "error": "Unknown operation"
            }

class DeviceManagerService(Service):
    """Manages device drivers and hardware access"""
    
    def __init__(self):
        super().__init__("device_manager")
        self.devices = {}
        self.driver_processes = {}
        
    def initialize(self, kernel):
        super().initialize(kernel)
        # Auto-discover available drivers
        self._discover_drivers()
        
    def _discover_drivers(self):
        """Discover available drivers in the drivers package"""
        try:
            import drivers
            import pkgutil
            
            for _, name, _ in pkgutil.iter_modules(drivers.__path__):
                self.devices[name] = {
                    "status": "available",
                    "driver": name,
                    "loaded": False
                }
                logging.info(f"Discovered driver: {name}")
        except ImportError:
            logging.warning("No drivers package found")
        
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        operation = message.get("operation")
        
        if operation == "load_driver":
            driver_name = message.get("driver")
            return self._load_driver(driver_name)
            
        elif operation == "unload_driver":
            driver_name = message.get("driver")
            return self._unload_driver(driver_name)
            
        elif operation == "list_devices":
            return {
                "status": "success",
                "operation": "list_devices",
                "devices": self.devices
            }
            
        else:
            return {
                "status": "error",
                "operation": operation,
                "error": "Unknown operation"
            }
            
    def _load_driver(self, driver_name: str) -> Dict[str, Any]:
        """Load a device driver as a process"""
        if driver_name not in self.devices:
            return {
                "status": "error",
                "operation": "load_driver",
                "driver": driver_name,
                "error": "Driver not found"
            }
            
        if self.devices[driver_name]["loaded"]:
            return {
                "status": "success",
                "operation": "load_driver",
                "driver": driver_name,
                "message": "Driver already loaded"
            }
            
        try:
            # Import the driver module
            driver_module = importlib.import_module(f"drivers.{driver_name}")
            
            # Create a process for the driver
            pid = str(uuid.uuid4())
            process = Process(
                pid=pid,
                name=f"driver-{driver_name}",
                target=driver_module.run,
                args=(self.kernel,)
            )
            
            # Register and start the process
            self.kernel.register_process(process)
            process.start()
            
            # Update device status
            self.devices[driver_name]["loaded"] = True
            self.devices[driver_name]["status"] = "active"
            self.devices[driver_name]["pid"] = pid
            self.driver_processes[driver_name] = pid
            
            return {
                "status": "success",
                "operation": "load_driver",
                "driver": driver_name,
                "pid": pid
            }
            
        except Exception as e:
            logging.error(f"Failed to load driver {driver_name}: {e}")
            return {
                "status": "error",
                "operation": "load_driver",
                "driver": driver_name,
                "error": str(e)
            }
            
    def _unload_driver(self, driver_name: str) -> Dict[str, Any]:
        """Unload a device driver"""
        if driver_name not in self.devices:
            return {
                "status": "error",
                "operation": "unload_driver",
                "driver": driver_name,
                "error": "Driver not found"
            }
            
        if not self.devices[driver_name]["loaded"]:
            return {
                "status": "success",
                "operation": "unload_driver",
                "driver": driver_name,
                "message": "Driver not loaded"
            }
            
        try:
            # Get process ID
            pid = self.driver_processes[driver_name]
            
            # Terminate the process
            self.kernel.terminate_process(pid)
            
            # Update device status
            self.devices[driver_name]["loaded"] = False
            self.devices[driver_name]["status"] = "available"
            del self.devices[driver_name]["pid"]
            del self.driver_processes[driver_name]
            
            return {
                "status": "success",
                "operation": "unload_driver",
                "driver": driver_name
            }
            
        except Exception as e:
            logging.error(f"Failed to unload driver {driver_name}: {e}")
            return {
                "status": "error",
                "operation": "unload_driver",
                "driver": driver_name,
                "error": str(e)
            }

class ProcessScheduler(Service):
    """Handles process scheduling and management"""
    
    def __init__(self):
        super().__init__("scheduler")
        
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        operation = message.get("operation")
        
        if operation == "list_processes":
            processes = self.kernel.get_processes()
            return {
                "status": "success",
                "operation": "list_processes",
                "processes": [
                    {
                        "pid": pid,
                        "name": process.name,
                        "running": process.running
                    }
                    for pid, process in processes.items()
                ]
            }
            
        elif operation == "terminate_process":
            pid = message.get("pid")
            success = self.kernel.terminate_process(pid)
            return {
                "status": "success" if success else "error",
                "operation": "terminate_process",
                "pid": pid,
                "error": None if success else "Process not found or could not be terminated"
            }
            
        else:
            return {
                "status": "error",
                "operation": operation,
                "error": "Unknown operation"
            }

class MicroKernel:
    """Enhanced microkernel implementation"""
    
    def __init__(self):
        self.system_queue = queue.Queue()
        self.running = True
        self.services = {}
        self.processes = {}
        self.logger = logging.getLogger("Kernel")
        
    def start(self):
        """Start the kernel"""
        self.logger.info("Kernel starting...")
        
        # Register core services
        self._register_core_services()
        
        # Start the main kernel loop
        threading.Thread(
            target=self.kernel_loop, 
            daemon=True, 
            name="KernelLoop"
        ).start()
        
    def _register_core_services(self):
        """Register the core services"""
        self.register_service(FileSystemService())
        self.register_service(DeviceManagerService())
        self.register_service(ProcessScheduler())
        
    def register_service(self, service: Service):
        """Register a service with the kernel"""
        service.initialize(self)
        self.services[service.name] = service
        self.logger.info(f"Service '{service.name}' registered")
        
    def register_process(self, process: Process):
        """Register a process with the kernel"""
        self.processes[process.pid] = process
        self.logger.info(f"Process '{process.name}' (PID: {process.pid}) registered")
        
    def get_processes(self) -> Dict[str, Process]:
        """Get all registered processes"""
        return self.processes
        
    def terminate_process(self, pid: str) -> bool:
        """Terminate a process by PID"""
        if pid in self.processes:
            process = self.processes[pid]
            process.terminate()
            self.logger.info(f"Process '{process.name}' (PID: {pid}) terminated")
            # Remove process from registry after giving it time to exit
            time.sleep(0.1)
            if pid in self.processes:
                del self.processes[pid]
            return True
        return False
        
    def kernel_loop(self):
        """Main kernel loop"""
        self.logger.info("Kernel loop started")
        
        while self.running:
            try:
                message = self.system_queue.get(timeout=1)
                self.logger.debug(f"Received message: {message}")
                self.process_message(message)
            except queue.Empty:
                # Just continue the loop
                pass
            
            # Cleanup terminated processes
            self._cleanup_processes()
            
    def _cleanup_processes(self):
        """Remove terminated processes from the registry"""
        terminated = [pid for pid, proc in self.processes.items() if not proc.running]
        for pid in terminated:
            self.logger.info(f"Cleaning up terminated process {pid}")
            del self.processes[pid]
            
    def process_message(self, message: Dict[str, Any]):
        """Process a message from the system queue"""
        service_name = message.get("service")
        sender_pid = message.get("sender")
        reply_to = message.get("reply_to")
        
        if service_name in self.services:
            service = self.services[service_name]
            self.logger.debug(f"Routing message to service: {service_name}")
            
            # Process the message
            result = service.process_message(message)
            
            # Send reply if needed
            if reply_to and reply_to in self.processes:
                reply = {
                    "type": "reply",
                    "original_request": message,
                    "result": result,
                    "service": service_name
                }
                self.processes[reply_to].send_message(reply)
                
        else:
            self.logger.warning(f"Service not found: {service_name}")
            
            # Send error reply
            if reply_to and reply_to in self.processes:
                error_reply = {
                    "type": "reply",
                    "original_request": message,
                    "result": {
                        "status": "error",
                        "error": f"Service not found: {service_name}"
                    }
                }
                self.processes[reply_to].send_message(error_reply)
                
    def send_system_message(self, message: Dict[str, Any]):
        """Send a message to the system queue"""
        self.system_queue.put(message)
        
    def create_process(self, name: str, target: Callable, args=(), kwargs={}) -> str:
        """Create a new process"""
        pid = str(uuid.uuid4())
        process = Process(pid=pid, name=name, target=target, args=args, kwargs=kwargs)
        self.register_process(process)
        process.start()
        return pid
        
    def stop(self):
        """Stop the kernel"""
        self.logger.info("Kernel shutting down...")
        self.running = False
        
        # Terminate all processes
        for pid in list(self.processes.keys()):
            self.terminate_process(pid)
            
        self.logger.info("Kernel shutdown complete")

# Example driver function
def example_driver_process(process, kernel):
    """Example driver process function"""
    logger = logging.getLogger(f"Driver-{process.name}")
    logger.info("Driver started")
    
    while process.running:
        # Simulate sensor readings
        kernel.send_system_message({
            "service": "device_manager",
            "operation": "sensor_reading",
            "sensor": process.name,
            "value": time.time() % 100,
            "sender": process.pid
        })
        
        # Check for messages
        message = process.receive_message(timeout=1)
        if message:
            logger.info(f"Received message: {message}")
            
        time.sleep(2)
        
    logger.info("Driver stopped")

# Flask API integration function
def create_flask_api(kernel):
    """Create a Flask API for interacting with the microkernel"""
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    
    @app.route('/api/services', methods=['GET'])
    def list_services():
        """List all available services"""
        return jsonify({
            "services": list(kernel.services.keys())
        })
        
    @app.route('/api/processes', methods=['GET'])
    def list_processes():
        """List all running processes"""
        result = kernel.services["scheduler"].process_message({
            "operation": "list_processes"
        })
        return jsonify(result)
        
    @app.route('/api/devices', methods=['GET'])
    def list_devices():
        """List all devices"""
        result = kernel.services["device_manager"].process_message({
            "operation": "list_devices"
        })
        return jsonify(result)
        
    @app.route('/api/devices/<driver_name>/load', methods=['POST'])
    def load_driver(driver_name):
        """Load a device driver"""
        result = kernel.services["device_manager"].process_message({
            "operation": "load_driver",
            "driver": driver_name
        })
        return jsonify(result)
        
    @app.route('/api/devices/<driver_name>/unload', methods=['POST'])
    def unload_driver(driver_name):
        """Unload a device driver"""
        result = kernel.services["device_manager"].process_message({
            "operation": "unload_driver",
            "driver": driver_name
        })
        return jsonify(result)
        
    @app.route('/api/fs/files', methods=['GET'])
    def list_files():
        """List all files in the filesystem"""
        result = kernel.services["filesystem"].process_message({
            "operation": "list"
        })
        return jsonify(result)
        
    @app.route('/api/fs/files/<path:file_path>', methods=['GET'])
    def get_file(file_path):
        """Get the contents of a file"""
        result = kernel.services["filesystem"].process_message({
            "operation": "read",
            "path": file_path
        })
        return jsonify(result)
        
    @app.route('/api/fs/files/<path:file_path>', methods=['POST'])
    def create_file(file_path):
        """Create or update a file"""
        content = request.json.get('content', '')
        result = kernel.services["filesystem"].process_message({
            "operation": "write",
            "path": file_path,
            "content": content
        })
        return jsonify(result)
        
    @app.route('/api/process/<pid>/terminate', methods=['POST'])
    def terminate_process(pid):
        """Terminate a process"""
        result = kernel.services["scheduler"].process_message({
            "operation": "terminate_process",
            "pid": pid
        })
        return jsonify(result)
        
    return app

if __name__ == "__main__":
    # Create and start the kernel
    kernel = MicroKernel()
    kernel.start()
    
    # Create a test process
    kernel.create_process(
        name="test-driver",
        target=example_driver_process,
        args=(kernel,)
    )
    
    # Create and run Flask API
    app = create_flask_api(kernel)
    
    try:
        # Run Flask in a separate thread
        flask_thread = threading.Thread(
            target=lambda: app.run(debug=False, host='0.0.0.0', port=5000),
            daemon=True
        )
        flask_thread.start()
        
        # Keep the main thread running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        pass
    finally:
        kernel.stop()
