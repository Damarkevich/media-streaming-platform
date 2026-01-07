#!/bin/sh

# Create migrations
python manage.py makemigrations --noinput

# Run database migrations
python manage.py migrate --noinput

# Start gunicorn
exec gunicorn config.wsgi --bind 0.0.0.0:8000
