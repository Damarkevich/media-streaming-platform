# ETL Service: PostgreSQL to Elasticsearch

A robust ETL (Extract, Transform, Load) pipeline that synchronizes movie-related data from PostgreSQL to Elasticsearch. The service continuously monitors database changes and keeps the search index up-to-date with incremental updates.

## 🎯 Overview

This service is part of a media streaming platform and serves as the data synchronization layer between the transactional database (PostgreSQL) and the search engine (Elasticsearch). It ensures that all movie catalog changes are reflected in the search index in near real-time.

### Key Features

- **Incremental Synchronization**: Tracks last modified timestamps to process only new or updated records
- **Batch Processing**: Configurable batch size for optimal memory usage and performance
- **State Persistence**: Redis-based state management to resume from last checkpoint after restarts
- **Automatic Retry Logic**: Built-in retry mechanism with jitter to handle transient failures
- **Continuous Monitoring**: Runs in an infinite loop to maintain data consistency
- **YAML-based Configuration**: Flexible mapping configuration for different entity types
- **Automatic Schema Setup**: Creates Elasticsearch indices and mappings on startup

## 📚 Logic Description

### Architecture

The pipeline follows the classic ETL pattern with state management:

```
┌──────────────────┐
│   PostgreSQL     │  Source database (film_work, person, genre)
└────────┬─────────┘
         │ Extract
┌────────▼─────────┐
│   Extractor      │  Batch retrieval with modified timestamp tracking
└────────┬─────────┘
         │ Transform
┌────────▼─────────┐
│  Transformer     │  Convert DB records to ES documents
└────────┬─────────┘
         │ Load
┌────────▼─────────┐
│  Elasticsearch   │  Search index (movies, persons, genres)
└──────────────────┘
         ▲
         │ State Storage
┌────────┴─────────┐
│      Redis       │  Persist last processed timestamps
└──────────────────┘
```

### Data Flow

1. **State Check** → Read last processed timestamp for each table from Redis
2. **Extract** → Query PostgreSQL for modified records since last timestamp
3. **Transform** → Convert database records to Elasticsearch document format
4. **Load** → Bulk index transformed documents to Elasticsearch
5. **State Update** → Store new timestamp in Redis for next iteration
6. **Repeat** → Process next table or wait before next cycle

### Core Components

#### Tables Monitored
- **film_work** - Movies and their metadata
- **person** - Cast and crew information
- **genre** - Movie genres and categories

#### Processing Strategy
Each table is processed sequentially in a continuous loop:
1. Check for modifications in `person` table
2. Check for modifications in `genre` table
3. Check for modifications in `film_work` table
4. Brief pause before next cycle

### ETL Mappings

The service uses YAML-based configuration (`etl_mappings.yaml`) to define how each PostgreSQL table maps to Elasticsearch indices, including field transformations and relationships.

## 🛠 Tech Stack

### Core Technologies

- **Python 3.14+** - Programming language
- **uv** - Fast Python package manager
- **PyYAML 6.0+** - YAML configuration parsing

### Data Layer

- **PostgreSQL** - Source transactional database
- **Elasticsearch 9.2+** - Target search index
- **Redis 7.1+** - State persistence

### Key Libraries

- **psycopg 3.x** - PostgreSQL database adapter
- **redis** - Redis client for state management
- **requests** - HTTP client for Elasticsearch API
- **httpx** - Modern async-capable HTTP client
- **pydantic** - Data validation and settings management
- **python-dotenv** - Environment variable management

## 🚀 Getting Started

### Prerequisites

- Python 3.14 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- PostgreSQL database with movie data
- Elasticsearch cluster (local or remote)
- Redis server for state management

### Installation

1. **Clone the repository and navigate to the project:**
   ```bash
   cd etl_service
   ```

2. **Install dependencies using uv:**
   ```bash
   uv sync
   ```

3. **Configure environment variables:**
   
   Create a `.env` file in the project root:
   ```env
   # PostgreSQL Configuration
   POSTGRES_DB=movies_database
   POSTGRES_USER=app
   POSTGRES_PASSWORD=123qwe
   SQL_HOST=localhost
   SQL_PORT=5432
   SQL_OPTIONS=-c search_path=public,content

   # Elasticsearch Configuration
   ES_HOST=localhost
   ES_PORT=9200

   # Redis Configuration
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_DB=0

   # ETL Configuration
   BATCH_SIZE=1000
   
   # Logging Configuration
   LOG_LEVEL=INFO
   LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
   LOG_NAME=etl_postgres_to_elastic
   ```

### Running the Application

#### Development Mode

```bash
uv run main.py
```

#### Using Docker

```bash
docker build -t etl-service .
docker run --env-file .env etl-service
```

#### Full Stack with Docker Compose

From the project root:
```bash
docker-compose up --build -d
```

### Verify Installation

Check Elasticsearch indices were created:

```bash
curl http://localhost:9200/_cat/indices?v
```

Expected indices:
- `movies`
- `persons`
- `genres`

Check ETL service logs:
```bash
docker-compose logs -f etl-service
```

## 🏗 Project Structure

```
etl_service/
├── config/
│   ├── etl_mappings.py       # YAML mappings loader
│   ├── etl_mappings.yaml     # Table to index mapping configuration
│   ├── logger.py             # Logging configuration
│   ├── settings.py           # Environment-based settings
│   └── es_schemas/           # Elasticsearch index schemas
│       ├── movies.json       # Movies index mapping
│       ├── persons.json      # Persons index mapping
│       └── genres.json       # Genres index mapping
├── backoff.py                # Retry decorator with exponential backoff
├── extractor.py              # PostgreSQL data extraction logic
├── transformer.py            # Data transformation logic
├── loader.py                 # Elasticsearch loading logic
├── state.py                  # State management with Redis
├── state_setup.py            # Initialize state on startup
├── es_setup.py               # Elasticsearch index setup
├── main.py                   # Application entry point
├── Dockerfile                # Docker configuration
├── pyproject.toml            # Python dependencies
└── README.md                 # This file
```


## 📝 Development

### State Management

The ETL service uses Redis to persist the last processed timestamp for each table:

```
state:{table_name}:last_modified → ISO 8601 timestamp
```

This ensures that:
- Service can resume from last checkpoint after restart
- No data is processed twice
- Incremental updates are efficient

### Retry Logic

The service includes exponential backoff for handling failures:
- Automatic retry on transient errors
- Jitter to prevent thundering herd
- Configurable max retries and delays

## 📄 License

This project is part of the Media Streaming Platform.