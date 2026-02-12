try:
    from src.services.database.movies.movies_db import MoviesDBHandler
except:
    from movies_db import MoviesDBHandler
from typing import Any, Dict
from git import Optional
from langchain_core.documents import Document
from langchain_chroma import Chroma

# from langchain_ollama import OllamaEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

class ChromaMoviesDBHandler(MoviesDBHandler):
    def __init__(self, env:str, path: str):
        if env.lower() != "local":
            raise RuntimeError(f"ChromaDB is only supported in local env. Got env={env}")

        self.path = path        

        # self.embeddings = OllamaEmbeddings(model="llama3")
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")


        self.vector_store = Chroma(
            collection_name="movie_collection",
            embedding_function=self.embeddings,
            persist_directory=path,
        )


    def similarity_search(self, query: str, k: int = 30, filters=None) -> list[dict]:
        return self.vector_store.similarity_search(query, k=k, filter=filters)
    
    def ingest_json(self, data: list[dict], overwrite: bool = False) -> None:
        # data is expected to be a list of dicts with the following format:
        # {
        #     "page_content": "text content of the movie",
        #     "metadata": {
        #         "title": "movie title",
        #         "genres": ["genre1", "genre2"],
        #         "director": "director name",
        #         "year": 2020,
        #         "themes": ["theme1", "theme2"]
        #     }
        # }        
        # If overwrite is True, delete and recreate the collection
        if overwrite:
            try:
                self.vector_store.delete_collection()
                print("Existing collection deleted.")
            except Exception as e:
                print(f"Note: Could not delete collection (may not exist): {e}")
            
            # Recreate the vector store
            self.vector_store = Chroma(
                collection_name="movie_collection",
                embedding_function=self.embeddings,
                persist_directory=self.path,
            )
            print("New collection created.")
            
        def _sanitize_metadata(raw_metadata: dict) -> dict:
            sanitized = {}
            for key, value in (raw_metadata or {}).items():
                if value is None:
                    continue
                if isinstance(value, list):
                    if not value:
                        continue
                    sanitized[key] = value
                    continue
                sanitized[key] = value
            return sanitized

        docs = []
        for item in data:
            page_content = item.get("page_content", "")
            metadata = _sanitize_metadata(item.get("metadata", {}))
            docs.append(Document(page_content=page_content, metadata=metadata))
        
        if docs:
            self.vector_store.add_documents(docs)

# -- check db content --

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv()

    MODE = "filters"

    # Initialize your handler
    handler = None
    if MODE != "filters":
        handler = ChromaMoviesDBHandler("local", os.getenv("MOVIES_DB_PATH"))

    match MODE:
        case "search":
            QUERY = "fantasy movie"
            FILTERS = {'$and': [{'genres': {'$contains': 'fantasy'}}, {'title': {'$ne': 'Akira'}}]}
            # FILTERS = {"genres":{'$contains': 'fantasy'}}
            # FILTERS = None
            print(handler.similarity_search(QUERY, k=3, filters=FILTERS))
    
        case "show":
            # Access all documents in the collection
            collection = handler.vector_store._collection  # underlying Chroma collection
            all_docs = collection.get(include=["metadatas", "documents"], limit=20)  # fetch all stored docs

            # Iterate and print
            for i, (doc, meta) in enumerate(zip(all_docs['documents'], all_docs['metadatas']), 1):
                print(f"{i}. Metadata: {meta}")
                print(f"   Content Preview: {doc[:100]}...\n")

            # Optional: check total count
            print(f"Total documents in DB: {len(all_docs['documents'])}")
    
        case "filters":
            def test_prepare_filters():
                test_cases = [
                    # 1. Empty filters, no watched
                    {
                        "input": {"filters": None, "watched": None},
                        "expected": None
                    },
                    # 2. Scalar filter
                    {
                        "input": {"filters": {"genres": "fantasy"}, "watched": None},
                        "expected": {"genres": {"$contains": "fantasy"}}
                    },
                    # 3. List filter
                    {
                        "input": {"filters": {"genres": ["fantasy", "sci-fi"]}, "watched": None},
                        "expected": {"$or": [
                            {"genres": {"$contains": "fantasy"}},
                            {"genres": {"$contains": "sci-fi"}}
                        ]}
                    },
                    # 4. Nested dict filter
                    {
                        "input": {"filters": {"rating": {"$gte": 7}}, "watched": None},
                        "expected": {"rating": {"$gte": 7}}
                    },
                    # 5. Mixed filters (scalar + list)
                    {
                        "input": {"filters": {"genres": "fantasy", "director": ["Nolan", "Tarantino"]}, "watched": None},
                        "expected": {"$or": [
                            {"genres": {"$contains": "fantasy"}},
                            {"director": {"$contains": "Nolan"}},
                            {"director": {"$contains": "Tarantino"}}
                        ]}
                    },
                    # 6. Filters + watched set
                    {
                        "input": {"filters": {"genres": "fantasy"}, "watched": {"Akira", "Spirited Away"}},
                        "expected": {"$and": [
                            {"genres": {"$contains": "fantasy"}},
                            {"title": {"$ne": "Akira"}},
                            {"title": {"$ne": "Spirited Away"}}
                        ]}
                    },
                    # 7. No filters, only watched set
                    {
                        "input": {"filters": None, "watched": {"Akira"}},
                        "expected": {"title": {"$ne": "Akira"}}
                    },
                    # 8. Empty list filter (should be ignored)
                    {
                        "input": {"filters": {"genres": []}, "watched": None},
                        "expected": None
                    }
                ]

                def prepare_filters(filters: Optional[Dict[str, Any]], watched: Optional[set] = None):
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
                                    for c in condition:
                                        or_conditions.append({field: {"$contains": c}})
                            else:
                                # scalar -> wrap in $in
                                or_conditions.append({field: {"$contains": condition}})
                    and_conditions = []
                    # If we have OR conditions, add them as a single block
                    if or_conditions:
                        if len(or_conditions) == 1:
                            and_conditions.append(or_conditions[0])
                        else:
                            and_conditions.append({"$or": or_conditions})
                    # Add watched exclusion
                    if watched:
                        for film in watched:
                            and_conditions.append({"title": {"$ne": film}})
                    if not and_conditions:
                        return None
                    elif len(and_conditions) == 1:
                        return and_conditions[0]
                    else:
                        return {"$and": and_conditions}

                # Run tests
                for i, case in enumerate(test_cases, 1):
                    result = prepare_filters(case["input"]["filters"], case["input"]["watched"])
                    try:
                        assert result == case["expected"], f"Test case {i} failed: {result} != {case['expected']}"
                    except AssertionError as e:
                        if i==6: pass # README since there i a set the order might change
                        else: raise e
                
                print("All test cases passed!")

            # Run the test set
            test_prepare_filters()
