FROM python:3.14-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.9.18 /uv /uvx /bin/

# Install curl for container healthchecks.
RUN apt-get update \
	&& apt-get install -y --no-install-recommends curl \
	&& rm -rf /var/lib/apt/lists/*


# Copy only dependency files first for better caching
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy the rest of the application
COPY . .

# Run the application.
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]