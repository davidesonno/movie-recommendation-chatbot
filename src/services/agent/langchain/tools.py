import json
import os
from langchain.tools import tool, ToolRuntime
from dataclasses import dataclass
from typing import Any, Dict, Optional
from langchain_community.tools import BraveSearch


# -- context --

@dataclass
class UserContext:
    user_id: int

# -- preferences --

@tool(
    "get_preferences",
    description=(
        "Return the user's structured preferences. "
        "Use when you need the user's saved preferences."
        ).strip()
)
def get_preferences_tool(runtime: ToolRuntime[UserContext]) -> str:
    store = runtime.store
    user_id = runtime.context.user_id
    preferences = store.get("preferences", user_id)
    return json.dumps(preferences or {}, indent=None)


def merge_preferences(current: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    merged = current.copy()
    for key, new_value in new.items():
        if key in merged:
            old_value = merged[key]
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                merged[key] = merge_preferences(old_value, new_value)
            elif isinstance(old_value, list) and isinstance(new_value, list):
                # extend lists but avoid duplicates
                merged[key] = old_value + [v for v in new_value if v not in old_value]
            else:
                merged[key] = new_value  # override scalar values
        else:
            merged[key] = new_value
    return merged


@tool(
    "upsert_preferences",
    description=(
        "Use this to update or add any user preferences you want, including inferred ones. "
        "Provide a preferences JSON object with the fields to change. "
        "If the user liked a movie, place it in the watched_films list. If they expressed interest but haven't watched it, place it in the interested_films list. "
        "Example: {'preferences':{'favorite_genres': ['sci-fi'], 'min_year': 2000}}. "
    ).strip()
)
def upsert_preferences_tool(preferences: dict = {}, runtime: ToolRuntime[UserContext] = None) -> str:
    store = runtime.store
    user_id = runtime.context.user_id

    current_preferences = store.get("preferences", user_id) or {}

    updated_preferences = merge_preferences(current_preferences, preferences)

    store.put("preferences", user_id, updated_preferences)
    return json.dumps(updated_preferences, indent=2)


# -- movie recommendations --

import os
from src.services.database.movies.movies_db import get_movies_db_handler

movie_vectorstore = get_movies_db_handler(
    os.getenv("MOVIES_DB_ENV"),
    os.getenv("MOVIES_DB_PROVIDER"),
    os.getenv("MOVIES_DB_PATH"),
)


@tool(
    "recommend_movies",
    description=(
        "Retrieve movies with query:str and OPTIONAL filters:dict. The filters are in OR. "
        "Do not query 'films like [x]', 'action'. "
        "Query using topics not genres or titles. "
        "ONLY use the filters if user asked for them. "
        "Available filters are genres (string), director (string), year (int or range), themes (string), title (string or {'$nin': [...]}) for exclusion. "
    ).strip()
)
def recomend_movies(query: str, filters: Optional[Dict[str, Any]] = None, runtime: ToolRuntime[UserContext] = None) -> str:
    def prepare_filters(filters: Optional[Dict[str, Any]], watched: Optional[set] = None):
        """
        Prepare Chroma-compatible filter:
        - Clean empty filters
        - Wrap scalar values into $in lists
        - Combine field filters with $or
        - AND them with watched exclusion ($nin)
        """

        or_conditions = []
        if filters:
            for field, condition in filters.items():
                if isinstance(condition, dict):
                    # Remove empty nested lists
                    condition = {
                        op: val
                        for op, val in condition.items()
                        if not (isinstance(val, list) and len(val) == 0)
                    }
                    if condition:
                        or_conditions.append({field: condition})
                elif isinstance(condition, list):
                    if condition:
                        or_conditions.append({field: {"$in": condition}})
                else:
                    # scalar -> wrap in $in
                    or_conditions.append({field: {"$in": [condition]}})

        and_conditions = []

        # If we have OR conditions, add them as a single block
        if or_conditions:
            if len(or_conditions) == 1:
                and_conditions.append(or_conditions[0])
            else:
                and_conditions.append({"$or": or_conditions})

        # Add watched exclusion
        if watched:
            and_conditions.append({"title": {"$nin": list(watched)}})

        if not and_conditions:
            return None
        elif len(and_conditions) == 1:
            return and_conditions[0]
        else:
            return {"$and": and_conditions}


    DB_RETRIEVE_AMOUNT = 30    
    TOOL_RETURN_AMOUNT = 3

    store = runtime.store
    user_id = runtime.context.user_id

    preferences = store.get("preferences", user_id) or {}
    watched = set(preferences.get("watched_films", []))
    interested = set(preferences.get("interested_films", []))

    # sanitize agent filters and add watched films
    filters = prepare_filters(filters, watched)

    # retrieve filtered candidates from vector store
    docs = movie_vectorstore.similarity_search(query, k=DB_RETRIEVE_AMOUNT, filters=filters)

    candidates = []
    
    for d in docs:
        meta = d.metadata
        title = meta["title"]

        if title.lower() in {w.lower() for w in watched}:
            continue  # filter watched

        score = 0.0
        if any(g in meta.get("genres", []) for g in preferences.get("favorite_genres", [])):
            score += 2.0
        if meta.get("director") in preferences.get("favorite_directors", []):
            score += 1.0
        if title in interested:
            score += 0.5

        candidates.append({
            "title": title,
            "year": meta.get("year"),
            "genres": meta.get("genres"),
            "plot": d.page_content,
            "score": score
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)

    return json.dumps([ c["plot"] for c in candidates[:TOOL_RETURN_AMOUNT]])


# -- web search --

@tool(
    "web_search",
    description=(
        "Search the web for current movie info. Provide a query string. "
        "Return a JSON list of objects with title, snippet, and URL. "
        "Use this only for recent, time-sensitive info not in the knowledge base."
    ).strip()
)
def brave_search_tool(query: str, k: int = 3) -> str:
    print(f"Executing brave_search_tool with query: {query}")
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    tool = BraveSearch.from_api_key(api_key=api_key)
    result = tool.run(query)
    print(f"Found {len(result)} search results, keeping top {k}.")
    # print(f"Search result: {result}")
    return ". ".join([r["snippet"] for r in result[:k]])
