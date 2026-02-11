from src.services.movie_data import main as movie_data_main
from src.services.ingest import main as ingest_main


def main():
	movie_data_main()
	ingest_main()


if __name__ == "__main__":
	main()
