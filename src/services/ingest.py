def main():
    import sys
    from pathlib import Path
    from dotenv import load_dotenv
    import os
    import json
    
    # Add project root to path so absolute imports work
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from src.services.database.movies.movies_db import get_movies_db_handler

    print("Starting movie data ingest process...")
    load_dotenv()
    print("Environment variables loaded.")

    movie_data_source_type = os.getenv("MOVIE_DATA_SOURCE_TYPE")  
    movie_data_input_path = os.getenv("MOVIE_DATA_INPUT_PATH")
    overwrite_db = os.getenv("OVERWRITE_MOVIES_DB", "false").lower() in ("true", "1", "yes")

    print(f"Configuration loaded: SourceType={movie_data_source_type}, InputPath={movie_data_input_path}, Overwrite={overwrite_db}")

    print("Loading movie data...")
    with open(movie_data_input_path, "r", encoding="utf-8") as f:
        movies = f.read()
    print(f"Successfully loaded movie data. Length: {len(movies)} characters.")

    print("Initializing movies database handler...")
    movies_db_handler = get_movies_db_handler(
        env=os.getenv("MOVIES_DB_ENV"),
        provider=os.getenv("MOVIES_DB_PROVIDER"),
        db_path=os.getenv("MOVIES_DB_PATH")
    )

    print(f"Ingesting movies into database (overwrite={overwrite_db})...")
    match movie_data_source_type.upper():
        case "JSON":
            movies_data = json.loads(movies)
            movies_db_handler.ingest_json(movies_data, overwrite=overwrite_db)
        case _:
            raise RuntimeError(f"Unsupported movie data source type: {movie_data_source_type}")
    print("Movie data ingested successfully.")


if __name__ == "__main__":
    main()