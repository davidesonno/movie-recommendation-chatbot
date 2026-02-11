import uvicorn
import sys
from src.api.app_factory import create_app

def init_backend(services_config: dict, ready_event=None):
    host = None
    port = None
    server_bound = False

    for service in ["auth", "chat", "agent", "monitoring"]:
        conf = services_config.get(service, {})
        if conf.get("ENV") == "local":
            if not server_bound:
                host = conf.get("API_HOST", host)
                port = int(conf.get("API_PORT", port))
                server_bound = True
                break

    if not server_bound:
        if ready_event:
            ready_event.set()
        return

    try:
        app = create_app(services_config)
    except Exception as e:
        print(f"\nERROR: Failed to initialize backend: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        if ready_event:
            ready_event.set()  # Allow main thread to continue
        return

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    if ready_event:
        ready_event.set()
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nBackend shutdown requested")
    except Exception as e:
        print(f"\nERROR: Backend crashed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
