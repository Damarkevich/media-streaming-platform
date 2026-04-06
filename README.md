# media-streaming-platform
Microservices backend for an online cinema platform. Python 3.14 • FastAPI • Django • PostgreSQL • Elasticsearch • Redis • Docker • Nginx • uv

# Project Documentation

## 1. What is this

This project appears to be a software application that utilizes Docker containerization for deployment and orchestration. The project contains infrastructure-related configuration files, specifically Docker Compose setup for managing multi-container Docker applications.

## 3. Services

This platform consists of the following microservices:

### Core Services
- **movies-admin** - A Django-based admin interface for managing movies in the project.
- **async-api** - A FastAPI-based asynchronous API for accessing movies data from Elasticsearch in the project. 

### Supporting Services
- **sqlite-to-postgres** - A tool to migrate data from SQLite databases to PostgreSQL.
- **etl-postgres-elasticsearch** - ETL pipeline for transferring data from PostgreSQL to Elasticsearch. 

### Infrastructure
- **schema-design** - The database schema design for the media streaming platform.

## 4. How to run using docker-compose

To run this project using Docker Compose:

1. Navigate to the root directory.

2. To start only the local infrastructure needed for development:
    ```bash
    make dev-infra-up
    ```

   This starts PostgreSQL, Elasticsearch, Redis, and Jaeger only.
    PostgreSQL is exposed on `127.0.0.1:5432`.

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