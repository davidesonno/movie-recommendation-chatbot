import os
import sys
from src.api.main import init_backend
import threading

from src.config import SERVICES_CONFIG

def launch_ui():
    os.system("streamlit run src/ui/ui.py")


def main():
    services_config = SERVICES_CONFIG

    if any(service.get("ENV") == "local" for service in services_config.values()):
        # init backend if at least one service is hosted locally. Pass all the config because it might use the other services
        ready_event = threading.Event()
        print("Starting backend...")
        backend_thread = threading.Thread(
            target=init_backend, args=(services_config, ready_event), daemon=True)
        backend_thread.start()
        
        # Wait for backend to be ready with a timeout
        if not ready_event.wait(timeout=30):
            print("ERROR: Backend failed to initialize within 30 seconds", file=sys.stderr)
            print("Check the error messages above for details.", file=sys.stderr)
            return
        
        print("Backend is ready.")

    try:
        print("Launching UI...")
        launch_ui()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication terminated")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
