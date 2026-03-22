#!/bin/sh

# Create migrations
uv run manage.py makemigrations --noinput

# Run database migrations
uv run manage.py migrate --noinput

# Collect static files
uv run manage.py collectstatic --noinput

# Start gunicorn
exec uv run gunicorn config.wsgi --bind 0.0.0.0:8000
