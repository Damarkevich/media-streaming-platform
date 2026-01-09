FROM python:3.14

COPY --from=ghcr.io/astral-sh/uv:0.9.22 /uv /uvx /bin/

WORKDIR /opt/etl_service

ENV UV_NO_DEV=1

COPY pyproject.toml uv.lock ./

RUN  uv sync --locked

COPY . .

ENTRYPOINT ["uv", "run", "main.py"]