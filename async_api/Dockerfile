FROM python:3.14-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.9.18 /uv /uvx /bin/

# Install curl for container healthchecks.
RUN apt-get update \
	&& apt-get install -y --no-install-recommends curl \
	&& rm -rf /var/lib/apt/lists/*

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen

# Run the application.
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]