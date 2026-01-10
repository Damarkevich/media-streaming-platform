# Async API

A FastAPI-based asynchronous API for accessing movies data from Elasticsearch in the project. This Readme describes, how to run app locally.

## Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager
- Redis
- Elasticsearch

## Quick Start

1. **Clone and navigate to the project:**
    ```bash
    cd async_api
    ```

2. **Install dependencies:**
    ```bash
    uv sync
    ```

3. **Set up environment variables (if needed):**
    Configure Redis and Elasticsearch connection settings in your environment or configuration file.

4. **Run the development server:**
    ```bash
    uv run fastapi dev scr/main.py
    ```

The API will be available at `http://localhost:8000/api/`
API documentation will be available at `http://localhost:8000/api/openapi`