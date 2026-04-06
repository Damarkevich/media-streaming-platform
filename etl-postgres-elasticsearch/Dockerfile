FROM python:3.14

COPY --from=ghcr.io/astral-sh/uv:0.9.22 /uv /uvx /bin/


WORKDIR /opt/etl-postgres-elasticsearch
ENV UV_NO_DEV=1

# Copy only dependency files first for better caching
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen

# Copy the rest of the application
COPY . .

ENTRYPOINT ["uv", "run", "main.py"]