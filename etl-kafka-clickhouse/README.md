# ETL Service: Kafka to ClickHouse

A robust ETL (Extract, Transform, Load) pipeline that consumes user behavior events from Kafka and stores them in ClickHouse for analytics workloads.

## 🎯 Overview

This service is part of a media streaming platform and acts as the ingestion bridge between the event stream (Kafka) and analytical storage (ClickHouse).
It continuously polls Kafka, validates and normalizes incoming events, batches them, and writes the transformed rows to a distributed ClickHouse table.

### Key Features

- **Continuous Stream Consumption**: Polls Kafka in a long-running loop
- **Schema Validation**: Pydantic-based validation of event payloads
- **Flexible Timestamp Parsing**: Supports Unix timestamps and ISO datetime values
- **Batch-Oriented Loading**: Flushes by size threshold or max wait timeout
- **Retry with Exponential Backoff**: Retries transient ClickHouse insert failures
- **Manual Kafka Offset Commits**: Commits only after successful ClickHouse write
- **Cluster-Aware DDL Scripts**: Helper scripts for distributed table init/reset

## 📚 Logic Description

### Architecture

The pipeline follows a focused ETL flow:

```
┌──────────────────┐
│      Kafka       │  Topic with raw event JSON
└────────┬─────────┘
         │ Extract
┌────────▼─────────┐
│   Extractor      │  KafkaConsumer poll + manual commit
└────────┬─────────┘
         │ Transform
┌────────▼─────────┐
│  Transformer     │  Validation, normalization, enrichment
└────────┬─────────┘
         │ Load
┌────────▼─────────┐
│   ClickHouse     │  Distributed table for analytics
└──────────────────┘
```

### Processing Flow

1. **Poll Kafka** using configured batch size and poll timeout.
2. **Validate/Transform** each raw event via `RawEvent` schema.
3. **Accumulate batch** until either:
   - transformed batch size reaches `ETL_KAFKA_CLICKHOUSE_MIN_LOAD_BATCH_SIZE`, or
   - wait time reaches `ETL_KAFKA_CLICKHOUSE_BATCH_MAX_WAIT_SECONDS`.
4. **Insert into ClickHouse** with retry policy.
5. **Commit Kafka offsets** only after successful load (or after all-invalid batch skip).
6. **Repeat** continuously.

### Data Model Notes

- Required event fields: `event_id`, `user_id`, `session_id`, `event_timestamp`, `server_timestamp`
- Optional movie relation is extracted from `payload.movie_id` (invalid values are ignored)
- `context` and `payload` are stored as JSON strings in ClickHouse
- ClickHouse table uses monthly partitioning and 12-month TTL (see `clickhouse_init.py`)

## 🛠 Tech Stack

### Core Technologies

- **Python 3.14+**
- **uv**

### Messaging and Storage

- **Kafka 3.4+** (source stream)
- **ClickHouse 23+** (analytical destination)

### Key Libraries

- **kafka-python** - Kafka consumer
- **clickhouse-driver** - ClickHouse client
- **pydantic / pydantic-settings** - validation and settings
- **pytest** - test framework

## 🚀 Getting Started

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv)
- Running Kafka cluster
- Running ClickHouse server/cluster

### Installation

```bash
cd etl-kafka-clickhouse
uv sync
```

### Environment Variables

Create `.env` in `etl-kafka-clickhouse/` (or provide these via root `.env` in Docker Compose):

```env
# Logging
ETL_KAFKA_CLICKHOUSE_LOG_LEVEL=INFO
ETL_KAFKA_CLICKHOUSE_LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
ETL_KAFKA_CLICKHOUSE_LOG_NAME=etl_kafka_to_clickhouse

# ClickHouse connection
ETL_KAFKA_CLICKHOUSE_HOST=localhost
ETL_KAFKA_CLICKHOUSE_PORT=9000
CLICKHOUSE_DEFAULT_USER=default
CLICKHOUSE_DEFAULT_PASSWORD=change_me_default_password
ETL_KAFKA_CLICKHOUSE_DATABASE=events
ETL_KAFKA_CLICKHOUSE_TABLE=user_events
ETL_KAFKA_CLICKHOUSE_CLUSTER_NAME=company_cluster
ETL_KAFKA_CLICKHOUSE_RUN_DDL_ON_CLUSTER=true
ETL_KAFKA_CLICKHOUSE_LOCAL_DATABASE=shard
ETL_KAFKA_CLICKHOUSE_SHARDING_KEY=cityHash64(user_id)
ETL_KAFKA_CLICKHOUSE_REPLICATED_PATH_SUFFIX=v2

# Kafka connection
ETL_KAFKA_CLICKHOUSE_BOOTSTRAP_SERVERS='["kafka-0:9092","kafka-1:9092","kafka-2:9092"]'
ETL_KAFKA_CLICKHOUSE_API_VERSION=[3, 4]
ETL_KAFKA_CLICKHOUSE_TOPIC=events
ETL_KAFKA_CLICKHOUSE_GROUP_ID=etl-kafka-clickhouse-group
ETL_KAFKA_CLICKHOUSE_AUTO_OFFSET_RESET=earliest
ETL_KAFKA_CLICKHOUSE_MAX_EXTRACT_BATCH_SIZE=100
ETL_KAFKA_CLICKHOUSE_POLL_TIMEOUT_MS=1000

# Batch and retry behavior
ETL_KAFKA_CLICKHOUSE_MIN_LOAD_BATCH_SIZE=1000
ETL_KAFKA_CLICKHOUSE_BATCH_MAX_WAIT_SECONDS=5.0
ETL_KAFKA_CLICKHOUSE_IDLE_SLEEP_SECONDS=0.5
ETL_KAFKA_CLICKHOUSE_INSERT_MAX_RETRIES=3
ETL_KAFKA_CLICKHOUSE_INSERT_RETRY_BACKOFF_SECONDS=1.0
```

### Running the Application

Run ETL loop:

```bash
cd etl-kafka-clickhouse
uv run main.py
```

### ClickHouse DDL Management

Initialize databases and tables:

```bash
cd etl-kafka-clickhouse
uv run clickhouse_init.py
```

Reset tables and stale replica metadata:

```bash
cd etl-kafka-clickhouse
uv run clickhouse_reset.py
```

### Using Docker

Build image:

```bash
cd etl-kafka-clickhouse
docker build -t etl-kafka-clickhouse .
```

Run container:

```bash
docker run --env-file .env etl-kafka-clickhouse
```

### Running with Docker Compose

From repository root:

```bash
docker compose up -d kafka-0 kafka-1 kafka-2 zookeeper clickhouse-node1 clickhouse-node2 clickhouse-node3 clickhouse-node4 etl-kafka-clickhouse
```

Check ETL logs:

```bash
docker compose logs -f etl-kafka-clickhouse
```

## ✅ Testing

Run tests:

```bash
cd etl-kafka-clickhouse
uv run --group dev pytest -q tests
```

Current tests cover:

- transformer validation and conversion behavior
- settings validators for SQL identifiers and sharding key format
- ClickHouse init DDL generation path
- ClickHouse reset logic including stale replica cleanup paths

## 🏗 Project Structure

```
etl-kafka-clickhouse/
├── config/
│   ├── logger.py              # Logging setup
│   └── settings.py            # Pydantic settings and validators
├── extractor.py               # Kafka consumer wrapper
├── transformer.py             # Event validation and transformation
├── loader.py                  # ClickHouse insert logic with retries
├── clickhouse_init.py         # Create DB/tables (local + distributed)
├── clickhouse_reset.py        # Drop tables and stale replica cleanup
├── main.py                    # ETL loop entrypoint
├── tests/
│   ├── test_transformer.py
│   ├── test_settings.py
│   ├── test_clickhouse_init_script.py
│   └── test_clickhouse_reset_script.py
├── Dockerfile
├── pyproject.toml
└── README.md
```

## 📄 License

This project is part of the Media Streaming Platform.
