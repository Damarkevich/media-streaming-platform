FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv sync --no-dev

COPY . .

EXPOSE 8010

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8010"]
