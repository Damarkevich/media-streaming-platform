# ETL: Postgres to Elasticsearch

## Overview
ETL pipeline for transferring data from PostgreSQL to Elasticsearch. 

## Description

This ETL service synchronizes movie-related data from a PostgreSQL database to Elasticsearch. It continuously monitors changes in three related tables (`film_work`, `person`, and `genre`), extracts modified records, transforms them into Elasticsearch-compatible documents, and loads them into the search index.

### Key Features

- **Incremental Updates**: Tracks the last processed timestamp for each table to only sync new or modified records
- **Batch Processing**: Processes data in configurable batches to optimize performance
- **State Persistence**: Maintains ETL progress state to resume from the last checkpoint
- **Automatic Retry Logic**: Includes delays to handle transient failures gracefully
- **Continuous Monitoring**: Runs in a loop to keep Elasticsearch synchronized with the latest database changes

### Architecture

The pipeline follows a classic ETL pattern:

1. **Extract**: `PostgresExtractor` retrieves film work data related to modified records
2. **Transform**: `transform_data()` converts raw database records into Elasticsearch document format
3. **Load**: `send_to_elasticsearch()` indexes the transformed documents

The service processes each table (`person`, `genre`, `film_work`) sequentially in a continuous cycle, ensuring all related data stays in sync.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```