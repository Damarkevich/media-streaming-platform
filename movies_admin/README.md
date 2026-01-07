# Movies Admin Panel

A Django-based admin interface for managing movies in the Prakticum project. This Readme describes, how to run app locally.

## Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager

## Quick Start

1. **Clone and navigate to the project:**
    ```bash
    cd movies_admin
    ```

2. **Install dependencies:**
    ```bash
    uv sync
    ```

3. **Apply migrations:**
    ```bash
    uv run python manage.py migrate
    ```

4. **Create a superuser:**
    ```bash
    uv run python manage.py createsuperuser
    ```

5. **Run the development server:**
    ```bash
    uv run python manage.py runserver
    ```

The admin panel will be available at `http://localhost:8000/admin`