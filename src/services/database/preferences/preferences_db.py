from abc import ABC, abstractmethod
from typing import Dict, Optional


class PreferencesStore(ABC):
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def get_preferences(self, user_id: Optional[int]) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def upsert_preferences(self, user_id: Optional[int], preferences: Dict) -> None:
        raise NotImplementedError


def create_preferences_store(
        env: str,
        provider: str,
        path: str
    ) -> PreferencesStore:
    if env.lower() == "local":
        match provider.upper():
            case "TINYDB":
                from src.services.database.preferences.TinyDB_db import TinyPreferencesStore

                return TinyPreferencesStore(path)
            case _:
                raise NotImplementedError(f"Unsupported preferences store provider: {provider}")
    else: 
        raise NotImplementedError(f"Unsupported preferences store environment: {env}")