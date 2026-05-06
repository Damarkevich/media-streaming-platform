FROM python:3.12-slim

WORKDIR /opt/delivery-worker

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/

CMD ["uv", "run", "python", "-m", "src.main"]
