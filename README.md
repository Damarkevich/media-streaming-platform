# media-streaming-platform
Microservices backend for an online cinema platform. Python 3.14 • FastAPI • Django • PostgreSQL • Elasticsearch • Redis • Docker • Nginx • uv

# Project Documentation

## 1. What is this

This project appears to be a software application that utilizes Docker containerization for deployment and orchestration. The project contains infrastructure-related configuration files, specifically Docker Compose setup for managing multi-container Docker applications.

## 2. CI/CD

The project uses GitHub Actions for continuous integration and delivery. All workflows are configured to run on Python 3.12, 3.13, and 3.14.

### Available Workflows

- **CI Pipeline** ([ci.yml](.github/workflows/ci.yml)) - Combined linting and testing workflow
- **Linting** ([lint.yml](.github/workflows/lint.yml)) - Code quality checks with ruff
- **Testing** ([test.yml](.github/workflows/test.yml)) - Test execution with coverage

### Local Development

Install development tools:
```bash
# Install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
# or via pip
pip install uv

# Install ruff for linting and formatting
uv tool install ruff

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

Run quality checks locally:
```bash
# Check code style
ruff check .

# Auto-fix issues
ruff check --fix .

# Check formatting
ruff format --check .

# Apply formatting
ruff format .
```

See [.github/workflows/README.md](.github/workflows/README.md) for detailed CI/CD documentation.

## 3. Services

This platform consists of the following microservices:

### Core Services
- **movies-admin** - A Django-based admin interface for managing movies in the project.
- **async-api** - A FastAPI-based asynchronous API for accessing movies data from Elasticsearch in the project.

### Supporting Services
- **sqlite-to-postgres** - A tool to migrate data from SQLite databases to PostgreSQL.
- **etl-postgres-elasticsearch** - ETL pipeline for transferring data from PostgreSQL to Elasticsearch.
- **etl-kafka-clickhouse** - ETL pipeline scaffold for transferring events from Kafka to ClickHouse.

### Infrastructure
- **schema-design** - The database schema design for the media streaming platform.

## 4. How to run using docker-compose

To run this project using Docker Compose:

1. Navigate to the root directory.

2. To start only the local infrastructure needed for development:
    ```bash
    make dev-infra-up
    ```

  This starts PostgreSQL, two Elasticsearch nodes (application and ELK), Redis, MongoDB, Jaeger, GlitchTip, and observability services (Kibana, Logstash, Filebeat).
    PostgreSQL is exposed on `127.0.0.1:5432`, MongoDB on `127.0.0.1:27017`.

### GlitchTip (Sentry-compatible) setup

GlitchTip is included in local infra and available at http://localhost:8007.

On the first start (or after cleaning GlitchTip DB volumes), apply migrations:

```bash
docker compose run --rm glitchtip ./manage.py migrate
```

If web/worker containers were already running, restart them:

```bash
docker compose restart glitchtip glitchtip-worker
```

Then create an organization and project in GlitchTip UI and copy DSN to `.env`:

```dotenv
SENTRY_DSN=http://<public_key>@localhost:8007/<project_id>
```

This DSN is used by application services (`movies-auth`, `movies-async-api`, `movies-event_ingest`, `ugc`) via `sentry-sdk`.

3. Start the services using Docker Compose:
    ```bash
    docker-compose up
    ```

4. To run in detached mode (background):
    ```bash
    docker-compose up -d
    ```

5. To stop the services:
    ```bash
    docker-compose down
    ```


**Prerequisites:**
- Docker must be installed on your system
- Docker Compose must be installed on your system

## 5. API Documentation Endpoints

After starting the project, you can access the interactive API documentation (Swagger UI) for each service at the following URLs:

- **Async API (content service):**
  - Swagger UI: http://localhost/api/content/docs
  - OpenAPI JSON: http://localhost/api/content/openapi.json

- **Auth service:**
  - Swagger UI: http://localhost/api/auth/docs
  - OpenAPI JSON: http://localhost/api/auth/openapi.json

These endpoints are proxied through nginx and available when the corresponding containers are running.

## 6. Unified Logging with Request Tracking

All services send logs to a centralized ELK stack where they can be correlated by `request_id` (for HTTP services) or `batch_id` (for batch processes).

**Kibana URL:** http://localhost:5601
**ELK Elasticsearch:** http://localhost:9201

### Log Indices

Each log type is stored in a dedicated index:

- **`nginx-logs-*`** — Nginx access logs with request_id
- **`app-logs-*`** — FastAPI/Django application services (auth, api, admin) with request_id
- **`event_ingest-logs-*`** — Event ingest service (Flask HTTP) with request_id
- **`etl-logs-*`** — ETL batch processes (Kafka→ClickHouse, PostgreSQL→Elasticsearch) with batch_id
- **`docker-logs-*`** — Infrastructure logs (Kafka, PostgreSQL, Redis, ClickHouse, Zookeeper, etc.)

### Request Tracing (HTTP Services)

Every HTTP request through nginx receives a unique `request_id` that flows through all services:

1. **Nginx** generates `X-Request-Id` header and logs it in `nginx-logs-*`
2. **Backend services** (event_ingest, auth, api, admin) extract header and inject into all log entries
3. **Filebeat** captures Docker container logs with request_id in JSON
4. **Logstash** normalizes and routes to appropriate index
5. **Kibana** allows querying by `request_id` to trace request through all services

### Batch Process Tracing (ETL Services)

ETL batch processes generate a `batch_id` for correlation:

1. **ETL service** starts and generates unique `batch_id`
2. **All logs** during the batch cycle include `batch_id` for correlation
3. **Filebeat/Logstash** route to `etl-logs-*` index
4. **Kibana** allows querying by `batch_id` to trace one ETL cycle

### Quick Start

1. Start infrastructure: `make dev-infra-up`
2. Open Kibana: http://localhost:5601
3. Create Index Patterns (use `@timestamp` as timestamp field):
   - `nginx-logs-*`, `app-logs-*`, `event_ingest-logs-*`, `etl-logs-*`, `docker-logs-*`
4. Make a test request: `curl http://localhost/api/auth/docs`
5. In Kibana Discover → Select `app-logs-*` → Filter by `request_id`
6. See all logs from all services for that single HTTP request

### Log Format

**HTTP Services** (structured JSON with request_id):
```json
{
  "timestamp": "2026-04-18T10:30:45",
  "level": "INFO",
  "logger": "src.api.v1.auth",
  "message": "User authentication successful",
  "request_id": "12345-1713442245123-1-1",
  "module": "auth",
  "function": "authenticate"
}
```

**ETL Services** (structured JSON with batch_id):
```json
{
  "timestamp": "2026-04-18T10:30:45",
  "level": "INFO",
  "logger": "extractor",
  "message": "Extracted 150 raw events",
  "batch_id": "batch-550e8400-e29b-41d4-a716-446655440000",
  "module": "extractor",
  "function": "get_batch"
}
```

### Where Logging Is Configured

- Routing and index selection: `elk/logstash/pipeline/logstash.conf`
- Collection and enrichment: `elk/filebeat/filebeat.yml`
- Nginx request_id generation and propagation: `nginx.conf`
- Service-side request_id middleware and JSON formatters:
  - `auth/src/core/middleware.py`, `auth/src/core/structured_logger.py`
  - `async_api/src/core/middleware.py`, `async_api/src/core/structured_logger.py`
  - `event_ingest/src/core/request_id_middleware.py`, `event_ingest/src/core/structured_logger.py`
  - `movies_admin/config/middleware.py`, `movies_admin/config/logging_config.py`
- ETL batch correlation (batch_id):
  - `etl-kafka-clickhouse/config/structured_logger.py`
  - `etl-postgres-elasticsearch/config/structured_logger.py`

See [elk/README.md](./elk/README.md) for detailed architecture, log schema, and tracing examples.
