FROM python:3.14-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.9.18 /uv /uvx /bin/

# Install curl for container healthchecks.
RUN apt-get update \
	&& apt-get install -y --no-install-recommends curl \
	&& rm -rf /var/lib/apt/lists/*


WORKDIR /app
COPY . .
RUN uv sync --frozen

# Run DB migrations and then start the application.
CMD ["sh", "/app/entrypoint.sh"]