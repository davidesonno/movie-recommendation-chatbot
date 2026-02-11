from abc import ABC, abstractmethod
from typing import Optional, List, Dict



# -- Abstract Interfaces (for future extensibility) --

class AppDBHandler(ABC): 
    """Abstract interface for unified application database handler."""

    # User methods
    @abstractmethod
    def create_user(self, username: str, hashed_password: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[dict]:
        raise NotImplementedError

    # Conversation methods
    @abstractmethod
    def create_conversation(self, user_id: int) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_conversation(self, conversation_id: int) -> Optional[Dict]:
        raise NotImplementedError

    @abstractmethod
    def list_conversations(self, user_id: int) -> List[Dict]:
        raise NotImplementedError

    @abstractmethod
    def update_conversation_title(self, user_id: int, conversation_id: int, title: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_conversation(self, user_id: int, conversation_id: int) -> None:
        raise NotImplementedError

    # Message methods
    @abstractmethod
    def insert_message(self, user_id: int, conversation_id: Optional[int], role: str, content: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_conversation_messages(self, user_id: int, conversation_id: int, limit: int = 50) -> List[Dict]:
        raise NotImplementedError

    @abstractmethod
    def list_messages(self, user_id: int, limit: int = 50) -> List[Dict]:
        raise NotImplementedError


# -- factory --
def get_db_handler(env: str, provider: str, db_path: str) -> AppDBHandler:
    """Factory function to create database handler."""
    if env.lower() != "local":
        raise NotImplementedError(f"Unsupported DB environment: {env}")
    else:
        provider = provider.upper()
        match provider:
            case "SQLITE":
                from src.services.database.app.SQLite_db import SQLiteAppHandler

                return SQLiteAppHandler(db_path)
            case _:
                raise NotImplementedError(f"Unsupported DB provider: {provider}")