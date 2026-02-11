try:
    from src.services.database.movies.movies_db import MoviesDBHandler
except:
    from movies_db import MoviesDBHandler
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

    # Initialize your handler
    handler = ChromaMoviesDBHandler("local", os.getenv("MOVIES_DB_PATH"))

    # Access all documents in the collection
    collection = handler.vector_store._collection  # underlying Chroma collection
    all_docs = collection.get(include=["metadatas", "documents"])  # fetch all stored docs

    # Iterate and print
    for i, (doc, meta) in enumerate(zip(all_docs['documents'], all_docs['metadatas']), 1):
        title = meta.get('title', 'No Title')
        content_preview = doc[:100]  # first 100 chars
        print(f"{i}. Title: {title}")
        print(f"   Content: {content_preview}...\n")

    # Optional: check total count
    print(f"Total documents in DB: {len(all_docs['documents'])}")
