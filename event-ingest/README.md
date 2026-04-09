# Event Ingest Service for Movies Platform

Event ingestion service for collecting client-side behavior events from applications and forwarding them to Kafka for downstream analytics and processing.

## 🎯 Overview

This service is part of the media streaming platform and acts as the entry point for user interaction telemetry.
It accepts batches of events from authenticated users, validates each event payload, enriches events with server-side metadata, and publishes valid messages to a Kafka topic.

### Key Features

- **Authenticated Ingestion**: Protected endpoint with JWT access token validation
- **Batch Event Processing**: Accepts and processes event batches in a single request
- **Schema Validation**: Marshmallow-based validation of event structure and event type
- **Partial Acceptance**: Invalid events are rejected while valid events in the same batch are still accepted
- **Kafka Delivery**: Sends validated events to Kafka with user-based message key
- **Server-Side Enrichment**: Adds `user_id` and `server_timestamp` before publish
- **OpenAPI Documentation**: Swagger UI via Flasgger using YAML endpoint specification
- **Graceful Producer Shutdown**: Flush/close Kafka producer on process exit

## 📚 Logic Description

### Architecture

The service follows a compact layered flow:

```
┌──────────────────┐
│   HTTP Layer     │  Flask route + JWT guard
├──────────────────┤
│ Validation Layer │  Marshmallow schemas
├──────────────────┤
│ Publish Layer    │  Kafka producer
└──────────────────┘
```

### Request Processing Flow

1. Client sends `POST /api/v1/events/` with JWT and JSON payload containing `events`.
2. Service validates request shape (`events` exists and is a list).
3. Each event is validated against `EventApiSchema`.
4. Valid event is enriched with:
	 - `user_id` from JWT identity
	 - `server_timestamp` from server time
5. Event is serialized to JSON and sent to Kafka topic.
6. Service returns summary with accepted count, validation rejects, and delivery failures when Kafka confirmation is incomplete.
7. Validation errors are returned with structured `details` payload.

### Endpoint

#### Events (`/api/v1/events/`)

- `POST /` - ingest batch of events for authenticated user

Possible responses:

- `200` - batch processed, includes accepted/rejected counters
- `503` - batch partially failed during Kafka delivery, includes accepted count, validation rejects, and delivery failures
- `400` - invalid request payload format (`details` field with validation errors)
- `401` - missing or invalid JWT token
- `413` - request body exceeds `MAX_CONTENT_LENGTH`

## 🛠 Tech Stack

### Core

- **Python 3.14+**
- **Flask 3.1+**
- **gevent** (WSGI runtime via monkey patching)

### Validation, Auth, API Docs

- **marshmallow** (request schema validation)
- **flask-jwt-extended** (JWT auth)
- **flasgger** (Swagger/OpenAPI docs)

### Messaging & Config

- **kafka-python** (Kafka producer)
- **pydantic-settings** (environment-based config)

## 🚀 Getting Started

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv)
- Kafka broker reachable from this service
- JWT secret compatible with your auth setup

### Installation

```bash
cd event-ingest
uv sync
```

### Environment Variables

Create `.env` from `.env.example` and set real values:

```env
SERVICE_NAME=Event Ingest Service
SERVICE_DESCRIPTION=Event Ingest service for the Movies Streaming Platform

DEBUG=True

AUTHJWT_SECRET_KEY=replace_with_secure_key_32_chars_or_more
AUTHJWT_ALGORITHM=HS256

MAX_CONTENT_LENGTH=1048576

KAFKA_BOOTSTRAP_SERVERS='["localhost:9094"]'
KAFKA_TOPIC=events
```

Notes:

- `AUTHJWT_SECRET_KEY` must be at least 32 characters.
- `MAX_CONTENT_LENGTH` is in bytes (default 1 MB).

### Running the Application

Development run:

```bash
cd event-ingest
uv run src/app.py
```

App factory run (explicit Flask command):

```bash
cd event-ingest
uv run flask --app src.app:create_app run --host 0.0.0.0 --port 5000
```

For production WSGI deployments, use `src/wsgi_app.py` as the entrypoint.

### Running with Docker

Build the image:

```bash
cd event-ingest
docker build -t movies-event-ingest .
```

The container runs via Gunicorn with the `gevent` worker class and uses `src.wsgi_app:app` as the WSGI entrypoint.

### Running with Docker Compose

From the project root:

```bash
docker compose up -d movies-event-ingest nginx
```

When the full stack is running behind nginx, the ingest endpoint is available at:

- `http://localhost/api/v1/events/`

### API Documentation

Swagger UI is served by Flasgger at:

- `http://localhost:5000/apidocs/`

## 📖 API Example

Request:

```bash
curl -X POST "http://localhost:5000/api/v1/events/" \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer <access_token>" \
	-d '{
		"events": [
			{
				"event_id": "97f85827-c4a8-4b36-914d-43b8598f0772",
				"event_type": "page_view",
				"event_timestamp": 1744000000,
				"session_id": "eaf282fa-7fb8-46ab-8e4f-f4ff088fd39d",
				"context": {
					"device": "mobile",
					"browser": "Chrome"
				},
				"payload": {
					"page": "/movies"
				}
			}
		]
	}'
```

Successful response:

```json
{
	"status": "success",
	"events_accepted": 1,
	"events_rejected": 0
}
```

Partial delivery failure response example (`503`):

```json
{
	"status": "partial_failure",
	"details": "Some events failed to deliver to Kafka",
	"events_accepted": 1,
	"events_rejected": 0,
	"delivery_failures": 1
}
```

Validation error response example (`400`):

```json
{
	"details": {
		"events": [
			"'events' key should be a list"
		]
	}
}
```

## ✅ Testing

Run tests:

```bash
cd event-ingest
uv run --group test pytest -q
```

Current test coverage includes:

- JWT requirement on ingest endpoint
- Request validation branches
- Kafka publish behavior for valid events
- Mixed batch handling (accepted + rejected)
- Schema validation for supported event types
- Producer lifecycle shutdown behavior

Infrastructure validation performed for this service includes:

- `docker compose config` for root stack validation
- container image build validation for the `movies-event-ingest` service definition

## 🏗 Project Structure

```
event-ingest/
├── src/
│   ├── app.py              # Flask app factory and extension wiring
│   ├── api/
│   │   └── v1/
│   │       ├── events.py       # Events ingest endpoint blueprint
│   │       └── event_ingest.yml # Swagger specification for endpoint
│   ├── schemas.py          # Marshmallow schemas for event validation
│   ├── services/
│   │   └── event_ingest.py # Event batch processing service logic
│   ├── wsgi_app.py         # WSGI entrypoint with gevent monkey patching
│   └── core/
│       ├── config.py       # Pydantic settings and env parsing
│       ├── logger.py       # Logging configuration
│       └── producer_lifecycle.py # Kafka producer lifecycle helpers
├── tests/
│   ├── conftest.py         # Fixtures (fake Kafka producer, auth headers)
│   ├── test_api.py         # Endpoint behavior tests
│   ├── test_event_ingest_service.py # Service-layer behavior tests
│   ├── test_schemas.py     # Schema validation tests
│   └── test_lifecycle.py   # Producer shutdown lifecycle tests
├── pyproject.toml
└── README.md
```
