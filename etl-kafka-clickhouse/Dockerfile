FROM python:3.14

COPY --from=ghcr.io/astral-sh/uv:0.9.22 /uv /uvx /bin/

WORKDIR /opt/etl-kafka-clickhouse
ENV UV_NO_DEV=1

COPY pyproject.toml README.md ./
RUN uv sync

COPY . .

ENTRYPOINT ["uv", "run", "main.py"]
