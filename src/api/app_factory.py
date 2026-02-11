from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import auth, chat, agent, monitoring
from src.services.database import get_db_handler
from src.services.agent import get_agent_handler
from src.services.rate_limiter import init_rate_limiter


def create_app(services_config: dict) -> FastAPI:
    app = FastAPI(title="Local API Server")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --------------------
    # Initialize Rate Limiter
    # --------------------
    rate_limit_conf = services_config.get("rate_limit", {})
    requests_per_minute = rate_limit_conf.get("REQUESTS_PER_MINUTE", 60)
    requests_per_hour = rate_limit_conf.get("REQUESTS_PER_HOUR", 1000)
    init_rate_limiter(requests_per_minute, requests_per_hour)

    # --------------------
    # Initialize App Database
    # --------------------
    db_conf = services_config.get("app_db", {})
    db_handler = get_db_handler(
        env=db_conf.get("ENV"),
        provider=db_conf.get("PROVIDER"),
        db_path=db_conf.get("PATH"),
    )

    app.state.db = db_handler
    app.state.config = services_config

    # Initialize Agent
    agent_conf = services_config.get("agent", {})
    agent_handler = get_agent_handler(
        agent_conf,
        llm_config=services_config.get("llm", {}),
        preferences_db_config=services_config.get("preferences_db", {})
    )
    app.state.agent_handler = agent_handler

    # Initialize Routers
    auth_conf = services_config.get("auth", {})
    if auth_conf.get("ENV") == "local":
        app.include_router(auth.router)

    chat_conf = services_config.get("chat", {})
    if chat_conf.get("ENV") == "local":
        app.include_router(chat.router)

    agent_conf = services_config.get("agent", {})
    if agent_conf.get("ENV") == "local":
        app.include_router(agent.router)

    # Initialize Monitoring Router
    monitoring_conf = services_config.get("monitoring", {})
    if monitoring_conf.get("ENV") == "local":
        app.include_router(monitoring.router)

    return app
