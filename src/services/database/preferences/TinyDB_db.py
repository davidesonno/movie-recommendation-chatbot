from typing import Union
from pathlib import Path
import json

from src.services.database.preferences.preferences_db import PreferencesStore


class TinyPreferencesStore(PreferencesStore):
    """
    User preferences store backed by a JSON file.
    Shape:
    {
        "users": {
            "<user_id>": { ...preferences }
        }
    }
    """

    def __init__(self, path: str) -> None:
        self._db_path = Path(path)
        if not self._db_path.exists():
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_db({"users": {}})
        else:
            content = self._db_path.read_text(encoding="utf-8").strip()
            if not content:
                self._write_db({"users": {}})
            else:
                data = self._safe_load(content)
                if not isinstance(data, dict) or "users" not in data or not isinstance(data.get("users"), dict):
                    self._write_db({"users": {}})

    def _safe_load(self, raw: str) -> dict:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _read_db(self) -> dict:
        content = self._db_path.read_text(encoding="utf-8").strip()
        if not content:
            return {"users": {}}
        data = self._safe_load(content)
        if not isinstance(data, dict):
            return {"users": {}}
        users = data.get("users")
        if not isinstance(users, dict):
            return {"users": {}}
        return {"users": users}

    def _write_db(self, data: dict) -> None:
        self._db_path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")

    def get_preferences(self, user_id: Union[int, str]) -> dict:
        data = self._read_db()
        user_key = str(user_id)
        return dict(data.get("users", {}).get(user_key, {}))

    def upsert_preferences(self, user_id: Union[int, str], preferences: dict) -> None:
        data = self._read_db()
        user_key = str(user_id)
        user_record = {key: value for key, value in preferences.items() if key != "user_id"}
        users = data.get("users", {})
        existing = users.get(user_key, {})
        if not isinstance(existing, dict):
            existing = {}
        existing.update(user_record)
        users[user_key] = existing
        data["users"] = users
        self._write_db(data)
