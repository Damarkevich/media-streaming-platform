FROM python:3.14-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.9.18 /uv /uvx /bin/

# Install curl for container healthchecks.
RUN apt-get update \
	&& apt-get install -y --no-install-recommends curl \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files first for better caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy application source.
COPY . .

CMD ["uv", "run", "gunicorn", "--worker-class", "gevent", "--workers", "1", "--bind", "0.0.0.0:8000", "--chdir", "src", "wsgi_app:app"]
