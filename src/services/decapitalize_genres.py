import json
import os
from dotenv import load_dotenv


def main():
    print("Starting genre decapitalization process...")
    load_dotenv()
    
    movie_data_output_path = os.getenv("MOVIE_DATA_OUTPUT_PATH")
    
    if not movie_data_output_path:
        raise ValueError("MOVIE_DATA_OUTPUT_PATH environment variable not set")
    
    if not os.path.exists(movie_data_output_path):
        raise FileNotFoundError(f"Movie data file not found: {movie_data_output_path}")
    
    print(f"Loading movies from {movie_data_output_path}...")
    with open(movie_data_output_path, "r", encoding="utf-8") as f:
        movies = json.load(f)
    
    print(f"Loaded {len(movies)} movies.")
    print("Decapitalizing genres...")
    
    modified_count = 0
    for movie in movies:
        if "metadata" in movie and "genres" in movie["metadata"]:
            original_genres = movie["metadata"]["genres"]
            lowercased_genres = [genre.lower() for genre in original_genres]
            
            if original_genres != lowercased_genres:
                movie["metadata"]["genres"] = lowercased_genres
                modified_count += 1
    
    print(f"Modified {modified_count} movies with capitalized genres.")
    print(f"Saving updated movies to {movie_data_output_path}...")
    
    with open(movie_data_output_path, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=4)
    
    print("Genre decapitalization complete!")


if __name__ == "__main__":
    main()
