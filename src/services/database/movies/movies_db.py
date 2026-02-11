from abc import ABC, abstractmethod



class MoviesDBHandler(ABC):
    @abstractmethod
    def __init__(self) -> None:
        self.vector_store = None
        raise NotImplementedError
    
    @abstractmethod
    def similarity_search(self, query: str, k: int = 30) -> list[dict]:
        raise NotImplementedError
    
    @abstractmethod 
    def ingest_json(self, data: list[dict], overwrite: bool = False) -> None:
        raise NotImplementedError
    

def get_movies_db_handler(env, provider: str, db_path: str) -> MoviesDBHandler:

    provider = provider.upper()
    match provider:
        case "CHROMA":
            from src.services.database.movies.ChromaDB_db import ChromaMoviesDBHandler
        
            return ChromaMoviesDBHandler(env, db_path)
        case _:
            raise RuntimeError(f"Unsupported movies DB provider: {provider}")