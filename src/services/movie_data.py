import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


def main():
    from dotenv import load_dotenv
    import os

    print("Starting movie data fetch process...")
    load_dotenv()
    print("Environment variables loaded.")

    movie_data_source = os.getenv("MOVIE_DATA_SOURCE")
    movie_data_source_base_url = os.getenv("MOVIE_DATA_SOURCE_BASE_URL")
    movie_data_source_api_key = os.getenv("MOVIE_DATA_SOURCE_API_KEY")
    movie_data_output_path = os.getenv("MOVIE_DATA_OUTPUT_PATH")
    movie_amount = int(os.getenv("MOVIE_AMOUNT"))
    movie_output_format = os.getenv("MOVIE_OUTPUT_FORMAT")

    print(f"Configuration loaded: Source={movie_data_source}, Amount={movie_amount}, Format={movie_output_format}")

    movies = []

    match movie_data_source:
        case "TMDB":
            print(f"Fetching {movie_amount} movies from TMDB...")
            movies = fetch_tmdb_data(movie_data_source_base_url, movie_data_source_api_key, movie_amount)
            print(f"Successfully fetched {len(movies)} movies.")
        case _:
            # README if you are implementing a new source, be sure that the output matches this structure:
    #     {
    #     "page_content": "John Wick (2014) is a Action, Thriller film directed by Chad Stahelski. Themes include hitman, bratva (russian mafia), gangster, secret organization, revenge, murder, dog, retired, widower. Ex-hitman John Wick comes out of retirement to track down the gangsters that took everything from him.",
    #     "metadata": {
    #         "title": "John Wick",
    #         "genres": [
    #             "action",     <---- NON CAPITALIZED
    #             "thriller"    <---- NON CAPITALIZED
    #         ],
    #         "director": "Chad Stahelski",
    #         "year": 2014,
    #         "themes": [
    #             "hitman",
    #             "bratva (russian mafia)",
    #             "gangster",
    #             "secret organization",
    #             "revenge",
    #             "murder",
    #             "dog",
    #             "retired",
    #             "widower"
    #         ]
    #     }
    # },
            raise RuntimeError(f"Unsupported movie data source: {movie_data_source}")

    print(f"Saving movies to {movie_data_output_path}...")
    save_movies(movies, movie_data_output_path, movie_output_format)
    print("Movie data saved successfully.")


def fetch_tmdb_data(base_url: str, api_key: str, amount: int):
    popular_url = base_url + "/movie/popular"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json;charset=utf-8"
    }

    movies_raw = []
    per_page = 20
    pages = (amount + per_page - 1) // per_page
    print(f"Will fetch approximately {pages} page(s) from TMDB API...")

    for page in range(1, pages + 1):
        print(f"  Fetching page {page}/{pages}...")
        resp = requests.get(popular_url, params={"page": page}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        movies_raw.extend(data.get("results", []))
        print(f"    Retrieved {len(data.get('results', []))} movies. Total: {len(movies_raw)}/{amount}")

        if len(movies_raw) >= amount:
            print(f"  Reached target amount of {amount} movies.")
            break

    movies_raw = movies_raw[:amount]

    print("Enriching movies in parallel...")

    enriched = []

    MAX_WORKERS = 8

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for m in movies_raw:
            tmdb_id = m["id"]
            futures.append(
                executor.submit(enrich_movie, base_url, headers, tmdb_id)
            )

        for i, future in enumerate(as_completed(futures), start=1):
            try:
                result = future.result()
                if result:
                    enriched.append(result)
                if i % 50 == 0:
                    print(f"  Enriched {i}/{len(futures)}")
            except Exception as e:
                print(f"  ⚠️ Error enriching movie: {e}")

    return enriched


def enrich_movie(base_url: str, headers: dict, tmdb_id: int):
    # 1) Details
    details_resp = requests.get(f"{base_url}/movie/{tmdb_id}", headers=headers)
    if details_resp.status_code != 200:
        return None
    details = details_resp.json()

    title = details.get("title")
    overview = details.get("overview", "")
    release_date = details.get("release_date", "")
    year = int(release_date[:4]) if release_date else None
    genres = [g["name"] for g in details.get("genres", [])]
    tmdb_score = details.get("vote_average")
    imdb_id = details.get("imdb_id")

    # 2) Credits (director + main cast)
    credits_resp = requests.get(f"{base_url}/movie/{tmdb_id}/credits", headers=headers)
    credits = credits_resp.json() if credits_resp.status_code == 200 else {}

    crew = credits.get("crew", [])
    cast = credits.get("cast", [])

    directors = [p["name"] for p in crew if p.get("job") == "Director"]
    director = directors[0] if directors else None

    main_cast = [p["name"] for p in cast[:5]]

    # 3) Keywords (themes)
    keywords_resp = requests.get(f"{base_url}/movie/{tmdb_id}/keywords", headers=headers)
    keywords_data = keywords_resp.json() if keywords_resp.status_code == 200 else {}
    themes = [k["name"].lower() for k in keywords_data.get("keywords", [])]

    # 4) Build page_content
    parts = []
    if title and year:
        parts.append(f"{title} ({year})")
    if genres:
        parts.append(f"is a {', '.join(genres)} film")
    if director:
        parts.append(f"directed by {director}.")
    if themes:
        parts.append(f"Themes include {', '.join(themes)}.")
    if overview:
        parts.append(overview)

    page_content = " ".join(parts).strip()

    # 5) Build vector-ready object
    return {
        "page_content": page_content,
        "metadata": {
            "title": title,
            "genres": genres,
            "director": director,
            "year": year,
            "themes": themes,
            # "score": tmdb_score,
            # "imdb_id": imdb_id
        }
    }


def save_movies(movies, output_path, output_format):
    import json

    match output_format.lower():
        case "json":
            print(f"Saving {len(movies)} movies to {output_path} in JSON format...")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(movies, f, ensure_ascii=False, indent=4)
            print("File saved successfully.")
        case _:
            raise RuntimeError(f"Unsupported output format: {output_format}")


if __name__ == "__main__":
    main()
