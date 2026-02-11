# Movie Recommendations Assistant

A local AI-powered movie recommendation system with multi-service architecture. Users can chat with an intelligent assistant to get movie recommendations based on mood, genre, and preferences.

## Quick Start

### Prerequisites

- **Python 3.12.3**
- Virtual environment (recommended)

### Installation & Execution

1. **Set up virtual environment** (if not already done):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. **Install dependencies**:

   ```powershell
   pip install -r requirements.txt
   ```
3. **Configure environment**:
   Rename or copy `.env.example`  into `.env` with the required variables (see [Configuration](#configuration))
4. **Run the application**:

   ```powershell
   python app.py
   ```

   This will:

   - Start the backend services (if configured as local)
   - Launch the Streamlit UI in your browser

## Services Architecture

The application is built on a microservices architecture with the following services:

### 1. **Authentication Service**

- User registration and login with JWT tokens
- Secure password hashing (PBKDF2)
- Token-based session management
- Stateless authentication for scalability

### 2. **Chat/Messaging Service**

- Create and manage conversations
- Send/receive messages
- Organize conversations with titles
- Delete conversations and message history

### 3. **Agent/LLM Service**

- AI-powered movie recommendations
- Conversation context awareness
- Integration with OpenAI or local language models
- Personalized recommendations based on user preferences

### 4. **Database Services**

#### App Database (SQLite)

- User accounts and authentication
- Conversation metadata
- Message history
- Foreign key relationships with cascading deletes

#### Preferences Database (TinyDB)

- User movie preferences
- Viewing history tracking
- Recommendation weights

#### Movies Database (ChromaDB)

- Vector embeddings of movies
- Fast semantic search
- Movie metadata (title, genre, director, themes, year)
- Uses Hugging Face embeddings for retrieval

## API-Driven Architecture & Extensibility

All services communicate exclusively via **REST APIs**, enabling a completely modular and replaceable architecture:

### Benefits of API-First Design

- **Swappable Components**: Replace any service (auth, chat, agent) with an alternative implementation without changing client code
- **Provider Agnostic**: Easily swap database providers, LLM providers, or vector stores
- **Scalability**: Scale individual services independently based on demand

### Adding Custom Providers

The application supports pluggable providers for databases and services. To add a custom provider:

1. **Implement the Handler Interface**

   - Create a new handler class inheriting from the base handler
   - Example locations:
     - Database handlers: `src/services/database/{type}/{provider_name}_db.py`
     - LLM handlers: `src/services/agent/langchain/` (or your framework)
2. **Register the Handler**

   - Update the factory function to recognize your new provider
   - Example: `src/services/database/get_db_handler()` for databases
3. **Configure via Environment**

   - Add your provider to `.env`:
     ```env
     APP_DB_PROVIDER=your_provider_name
     MOVIES_DB_PROVIDER=your_vector_db_name
     LLM_PROVIDER=your_llm_provider
     ```

### Examples of Swappable Components

| Component      | Current               | Alternative Options                           |
| -------------- | --------------------- | --------------------------------------------- |
| Auth DB        | SQLite                | PostgreSQL, MongoDB, Firebase                 |
| Preferences DB | TinyDB                | Redis, Firestore                              |
| Vector DB      | ChromaDB              | Pinecone, Weaviate, Milvus, Qdrant            |
| LLM            | OpenAI                | Anthropic, Hugging Face, Azure OpenAI, Ollama |
| Embeddings     | Sentence Transformers | OpenAI, Cohere, Azure                         |

Adding a new provider requires only implementing the corresponding handler interface—no changes to the API layer or client code needed.

## Movie Database

The movie database comes **pre-installed** with a curated collection of popular movies. No initial setup is required.

### Customizing the Movie Database

Check the `.env.example` for the download and ingestion phase settings.

You have two options:

#### Option 1: Full Pipeline (Download + Ingest)

Run both download and ingest steps together:

```powershell
python download_and_ingest.py
```

This will:

1. Fetch movies from TMDB API
2. Enrich movie data with details, credits, and themes
3. Update the ChromaDB vector store

#### Option 2: Individual Steps

Run each step independently for more control:

**Step 1: Download & Process Movie Data**

```powershell
python src/services/movie_data.py
```

- Fetches movies from configured source (TMDB)
- Enriches with details, director, cast, themes
- Outputs to `MOVIE_DATA_OUTPUT_PATH` (JSON)
- Configure: `MOVIE_DATA_SOURCE`, `MOVIE_AMOUNT`, `MOVIE_DATA_SOURCE_API_KEY`

**Step 2: Ingest into Database**

```powershell
python src/services/ingest.py
```

- Loads movie data from `MOVIE_DATA_INPUT_PATH`
- Ingests into ChromaDB vector store
- Creates embeddings for semantic search
- Configure: `MOVIE_DATA_SOURCE_TYPE`, `OVERWRITE_MOVIES_DB`

## Project Structure

```
.
├── app.py                          # Main entry point
├── config.py                       # Configuration loader
├── download_and_ingest.py          # Movie data pipeline
├── requirements.txt                # Python dependencies
├── data/                           # Data directory
|   ├── app.db                      # Users, messages, conversations
│   ├── movies.json                 # Movie data
│   ├── preferences.json            # User preferences
│   └── movies/                     # ChromaDB storage
├── src/
│   ├── api/                        # FastAPI backend
│   │   ├── app_factory.py          # App initialization
│   │   ├── main.py                 # API server
│   │   └── routers/                # API endpoints
│   │       ├── auth.py             # Authentication
│   │       ├── chat.py             # Messaging
│   │       └── agent.py            # Agent/LLM
│   ├── services/                   # Business logic
│   │   ├── movie_data.py           # Download movies
│   │   ├── ingest.py               # Ingest to database
│   │   ├── agent/                  # AI agent logic
│   │   └── database/               # Database handlers
│   └── ui/                         # Streamlit interface
│       └── ui.py                   # Main UI
└── .env                            # Configuration (not in repo)
```

## Technology Stack

- **Frontend**: Streamlit
- **Backend**: FastAPI + Uvicorn
- **Authentication**: JWT (PyJWT) + Passlib
- **AI/ML**: LangChain + OpenAI + HuggingFace Embeddings
- **Vector DB**: ChromaDB
- **Databases**: SQLite, TinyDB, ChromaDB
- **LLM Integration**: groq API
- **Embeddings**: Sentence Transformers
