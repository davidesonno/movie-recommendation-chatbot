from abc import ABC, abstractmethod
from typing import Optional, Dict, List

from src.services.database.preferences.preferences_db import PreferencesStore, create_preferences_store

from langgraph.store.base import BaseStore

class AgentStore(BaseStore):
    def __init__(self, preferences_store: PreferencesStore, max_tool_outputs: int = 3):
        self.preferences_store = preferences_store
        self.tools_output_store: Dict[int, List[Dict]] = {}  # user_id -> list of tool outputs
        self.max_tool_outputs = max_tool_outputs

    def get(self, key:str, user_id: int) -> Optional[Dict | List[Dict]]:
        if key == "preferences":
            return self.preferences_store.get_preferences(user_id)
        elif key == "tools_output":
            return self.tools_output_store.get(user_id, [])
        return None

    def put(self, key:str, user_id: int, value: Dict) -> None:
        if key == "preferences":
            self.preferences_store.upsert_preferences(user_id, value)
        elif key == "tools_output":
            if user_id not in self.tools_output_store:
                self.tools_output_store[user_id] = []
            self.tools_output_store[user_id].append(value)
            # Keep only the last max_tool_outputs
            if len(self.tools_output_store[user_id]) > self.max_tool_outputs:
                self.tools_output_store[user_id] = self.tools_output_store[user_id][-self.max_tool_outputs:]

    # required
    def batch(self):  raise NotImplementedError
    def abatch(self): raise NotImplementedError


class AgentHandler(ABC):
    def __init__(self, config: dict = {}, llm_config: dict = {}, preferences_db_config: dict = {}) -> None:
        self._config = config
        self._llm_config = llm_config
        self._preferences_store = create_preferences_store(
            preferences_db_config.get("ENV"),
            preferences_db_config.get("PROVIDER"),
            preferences_db_config.get("PATH"),
        )
        self._agent_store = AgentStore(
            self._preferences_store,
        )

    @abstractmethod
    def process_message(
        self,
        user_id: Optional[int],
        content: str,
        history: List[Dict],
    ) -> str:
        raise NotImplementedError


# -- factory --

def get_agent_handler(agent_config: dict, llm_config: Dict, preferences_db_config: Dict) -> AgentHandler:
    framework = agent_config.get("FRAMEWORK", "LANGCHAIN").upper()
    env = agent_config.get("ENV", "local").lower()

    if env != "local":
        raise RuntimeError(f"Unsupported agent environment: {env}")
    else:
        match framework:
            case "LANGCHAIN":
                from src.services.agent.langchain import LangChainAgentHandler

                return LangChainAgentHandler(agent_config, llm_config, preferences_db_config)
            case _:
                raise RuntimeError(f"Unsupported agent framework: {framework}")
