FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.18 /uv /uvx /bin/

RUN groupadd --system app && useradd --system --gid app --create-home app

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

RUN chown -R app:app /app

USER app

EXPOSE 8010

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8010"]
