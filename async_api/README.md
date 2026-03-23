# Async API for Movies Platform

A high-performance asynchronous REST API built with FastAPI for accessing movies, genres, and persons data. The API provides search capabilities, filtering, pagination, and caching using Elasticsearch as the primary data store and Redis for caching.

## 🎯 Overview

This service is part of a media streaming platform and serves as the backend API for browsing movie catalogs, discovering content, and searching through films, genres, and cast/crew information.

### Key Features

- **Asynchronous Architecture**: Built with FastAPI and async/await for high concurrency
- **Full-Text Search**: Powered by Elasticsearch with fuzzy matching and field boosting
- **Response Caching**: Redis-based caching layer for improved performance
- **RESTful Design**: Clean API design with proper HTTP methods and status codes
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Health Monitoring**: Built-in health check endpoint for service monitoring
- **Type Safety**: Full type hints with Pydantic models for validation

## 📚 Logic Description

### Architecture

The application follows a layered architecture pattern:

```
┌─────────────────┐
│   API Layer     │  FastAPI routes, request validation
├─────────────────┤
│ Service Layer   │  Business logic, data transformation
├─────────────────┤
│   DB Layer      │  Elasticsearch & Redis clients
└─────────────────┘
```

### Data Flow

1. **Request** → API endpoint receives HTTP request with parameters
2. **Cache Check** → Check Redis cache for existing response
3. **Data Retrieval** → If cache miss, query Elasticsearch
4. **Transform** → Convert ES models to API schemas
5. **Cache Store** → Store response in Redis (300s TTL)
6. **Response** → Return JSON response to client

### Core Components

#### Films (`/api/v1/films`)
- List films with pagination and sorting
- Filter by genre
- Search by title and description (fuzzy matching, title boosted 3x)
- Get detailed film information including cast and crew

#### Genres (`/api/v1/genres`)
- List all available genres
- Get genre details by ID

#### Persons (`/api/v1/persons`)
- Search persons by name (fuzzy matching)
- Get person details with filmography
- List films featuring a specific person (as actor, director, or writer)

### Search Implementation

- **Multi-match queries** with fuzziness for typo tolerance
- **Field boosting** for relevance tuning (e.g., `title^3`)
- **Nested queries** for filtering by related entities (genres, persons)
- **Boolean queries** with `should` clauses for multi-field person search

## 🛠 Tech Stack

### Core Technologies

- **Python 3.14+** - Programming language
- **FastAPI 0.128+** - Modern async web framework
- **Pydantic 2.x** - Data validation and settings management
- **Uvicorn** - ASGI server

### Data Layer

- **Elasticsearch 9.2+** - Full-text search engine and primary data store
- **Redis 7.1+** - In-memory cache for response caching

### Key Libraries

- **elasticsearch[async]** - Async Elasticsearch client
- **redis[asyncio]** - Async Redis client
- **orjson** - Fast JSON serialization
- **pydantic-settings** - Environment-based configuration

### Development Tools

- **uv** - Fast Python package manager
- **FastAPI DevTools** - Hot reload and debugging

## 🚀 Getting Started

### Prerequisites

- Python 3.14 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Redis server (local or remote)
- Elasticsearch 9.x (local or remote)

### Installation

1. **Clone the repository and navigate to the project:**
   ```bash
   cd async_api
   ```

2. **Install dependencies using uv:**
   ```bash
   uv sync
   ```


### Running the Application

#### Development Mode (with hot reload)

```bash
uv run fastapi dev src/main.py
```

The API will be available at:
- **API Base URL**: http://localhost:8000/api/v1/
- **Health Check**: http://localhost:8000/api/health
- **API Documentation**: http://localhost:8000/api/openapi
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

#### Production Mode

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

#### Using Docker

```bash
docker build -t async-api .
docker run -p 8000:8000 --env-file .env async-api
```

### Verify Installation

Check that all services are running:

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "redis": "up",
    "elasticsearch": "up"
  }
}
```

## 📖 API Examples

### Get Films List
```bash
curl "http://localhost:8000/api/v1/films?page_size=10&sort=-imdb_rating"
```

### Search Films
```bash
curl "http://localhost:8000/api/v1/films/search?query=star%20wars"
```

### Get Film Details
```bash
curl "http://localhost:8000/api/v1/films/{film_id}"
```

### Search Persons
```bash
curl "http://localhost:8000/api/v1/persons/search?query=tom%20hanks"
```

### Get Person's Films
```bash
curl "http://localhost:8000/api/v1/persons/{person_id}/film"
```

## ✅ Testing

### Functional Test Coverage

Functional tests cover all public GET endpoints:

- `/api/health`
- `/api/v1/films`
- `/api/v1/films/search`
- `/api/v1/films/{film_id}`
- `/api/v1/genres`
- `/api/v1/genres/{genre_id}`
- `/api/v1/persons/search`
- `/api/v1/persons/{person_id}`
- `/api/v1/persons/{person_id}/film`

Covered scenarios include:

- happy path responses
- validation errors (`422`)
- not found cases (`404`)
- cache behavior (repeat request after source data cleanup)

### Run Functional Tests

Run all functional tests:

```bash
uv run --group test pytest -v tests/functional/src
```

Run with slowest tests report:

```bash
uv run --group test pytest -q tests/functional/src --durations=15
```


## 🏗 Project Structure

```
async_api/
├── src/
│   ├── api/              # API routes and endpoints
│   │   ├── v1/           # API version 1
│   │   │   ├── films.py      # Films endpoints
│   │   │   ├── genres.py     # Genres endpoints
│   │   │   ├── persons.py    # Persons endpoints
│   │   │   ├── schemas.py    # Pydantic response models
│   │   │   └── validators.py # Request validators
│   │   └── health.py     # Health check endpoint
│   ├── core/             # Core configuration
│   │   ├── config.py         # Settings management
│   │   ├── cache.py          # Redis caching decorator
│   │   ├── logger.py         # Logging configuration
│   │   └── lifespan.py       # App lifecycle management
│   ├── db/               # Database clients
│   │   ├── elastic.py        # Elasticsearch connection
│   │   └── redis.py          # Redis connection
│   ├── models/           # Data models
│   │   └── es_models.py      # Elasticsearch models
│   ├── services/         # Business logic layer
│   │   ├── films.py          # Film service
│   │   ├── genres.py         # Genre service
│   │   └── persons.py        # Person service
│   └── main.py           # Application entry point
├── Dockerfile            # Docker configuration
├── pyproject.toml        # Python dependencies
└── README.md             # This file
```

## 🔧 Configuration

All configuration is managed through environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | 127.0.0.1 | Redis server hostname |
| `REDIS_PORT` | 6379 | Redis server port |
| `CACHE_EXPIRE_IN_SECONDS` | 300 | Cache TTL in seconds |
| `ES_SCHEMA` | http:// | Elasticsearch protocol |
| `ES_HOST` | localhost | Elasticsearch hostname |
| `ES_PORT` | 9200 | Elasticsearch port |

## 📝 Development

### Code Quality

The project uses type hints throughout and follows Python best practices.

### Adding New Endpoints

1. Define Pydantic schemas in `src/api/v1/schemas.py`
2. Create service methods in `src/services/`
3. Add API routes in `src/api/v1/`
4. Apply `@cache()` decorator for cacheable endpoints

## 📄 License

This project is part of the Media Streaming Platform.