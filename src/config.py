from dotenv import load_dotenv
import os

load_dotenv()

# exposed for the ui
LOGIN_API_ENDPOINT = os.getenv("LOGIN_API_ENDPOINT")
REGISTER_API_ENDPOINT = os.getenv("REGISTER_API_ENDPOINT")
LOGOUT_API_ENDPOINT = os.getenv("LOGOUT_API_ENDPOINT")

CONVERSATION_LIST_ENDPOINT = os.getenv("CONVERSATION_LIST_ENDPOINT")
CONVERSATION_UPDATE_ENDPOINT = os.getenv("CONVERSATION_UPDATE_ENDPOINT")
CONVERSATION_DELETE_ENDPOINT = os.getenv("CONVERSATION_DELETE_ENDPOINT")

MESSAGE_SEND_ENDPOINT = os.getenv("MESSAGE_SEND_ENDPOINT")
MESSAGE_LIST_ENDPOINT = os.getenv("MESSAGE_LIST_ENDPOINT")

RATE_LIMIT_STATUS_ENDPOINT = os.getenv("RATE_LIMIT_STATUS_ENDPOINT")

SERVICES_CONFIG = {
    "auth": {
        "ENV": os.getenv("AUTH_ENV"),
        "API_HOST": os.getenv("AUTH_HOST"),
        "API_PORT": os.getenv("AUTH_PORT"),
        "BASE_URL": os.getenv("AUTH_BASE_URL"), 
        "LOGIN_API_ENDPOINT": LOGIN_API_ENDPOINT,
        "REGISTER_API_ENDPOINT": REGISTER_API_ENDPOINT,
        "LOGOUT_API_ENDPOINT": LOGOUT_API_ENDPOINT,
        "SECRET_KEY": os.getenv("SECRET_KEY"),
        "ALGORITHM": os.getenv("ALGORITHM", "HS256"),
        "ACCESS_TOKEN_EXPIRE_MINUTES": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)),
    },
    "chat": {
        "ENV": os.getenv("MESSAGING_ENV"),
        "API_HOST": os.getenv("MESSAGING_HOST"),
        "API_PORT": os.getenv("MESSAGING_PORT"),
        "BASE_URL": os.getenv("MESSAGING_BASE_URL"),
        "CONVERSATION_LIST_ENDPOINT": CONVERSATION_LIST_ENDPOINT,
        "CONVERSATION_CREATE_ENDPOINT": os.getenv("CONVERSATION_CREATE_ENDPOINT"),
        "CONVERSATION_UPDATE_ENDPOINT": CONVERSATION_UPDATE_ENDPOINT,
        "CONVERSATION_DELETE_ENDPOINT": CONVERSATION_DELETE_ENDPOINT,
        "MESSAGE_SEND_ENDPOINT": MESSAGE_SEND_ENDPOINT,
        "MESSAGE_LIST_ENDPOINT": MESSAGE_LIST_ENDPOINT,
    },
    "agent": {
        "ENV": os.getenv("AGENT_ENV"),
        "FRAMEWORK": os.getenv("AGENT_FRAMEWORK"),
        "API_HOST": os.getenv("AGENT_HOST"),
        "API_PORT": os.getenv("AGENT_PORT"),
        "BASE_URL": os.getenv("AGENT_BASE_URL"),
        "ENDPOINT": os.getenv("AGENT_ENDPOINT"),
        "BRAVE_SEARCH_API_KEY": os.getenv("BRAVE_SEARCH_API_KEY"),
        "AGENT_WEB_SEARCH": os.getenv("AGENT_WEB_SEARCH", "false").lower() == "true",
    },
    "llm": {
        "PROVIDER": os.getenv("LLM_PROVIDER"),
        "PROVIDER_BASE_URL": os.getenv("PROVIDER_BASE_URL"),
        "PROVIDER_API_KEY": os.getenv("PROVIDER_API_KEY"),
        "MODEL": os.getenv("LLM_MODEL"),
    },
    "app_db": {
        "ENV": os.getenv("APP_DB_ENV"),
        "PROVIDER": os.getenv("APP_DB_PROVIDER"),
        "PATH": os.getenv("APP_DB_PATH"),
    },
    "preferences_db": {
        "ENV": os.getenv("PREFERENCES_DB_ENV"),
        "PROVIDER": os.getenv("PREFERENCES_DB_PROVIDER"),
        "PATH": os.getenv("PREFERENCES_DB_PATH"),
    },
    "movies_db": {
        "ENV": os.getenv("MOVIES_DB_ENV"),
        "PROVIDER": os.getenv("MOVIES_DB_PROVIDER"),
        "PATH": os.getenv("MOVIES_DB_PATH"),
    },
    "rate_limit": {
        "REQUESTS_PER_MINUTE": int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", 60)),
        "REQUESTS_PER_HOUR": int(os.getenv("RATE_LIMIT_REQUESTS_PER_HOUR", 1000)),
    },
    "monitoring": {
        "ENV": os.getenv("MONITORING_ENV"),
        "API_HOST": os.getenv("MONITORING_HOST"),
        "API_PORT": os.getenv("MONITORING_PORT"),
        "BASE_URL": os.getenv("MONITORING_BASE_URL"),
        "ENDPOINT": os.getenv("RATE_LIMIT_STATUS_ENDPOINT"),
    },
}

for service_name, config in SERVICES_CONFIG.items():
    for key, value in config.items():
        if value is None:
            print(f"Warning: {service_name} config key {key} is not set in environment variables.")
