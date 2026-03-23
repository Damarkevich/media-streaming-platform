FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.22 /uv /uvx /bin/


WORKDIR /opt/movies_admin
ENV DJANGO_SETTINGS_MODULE 'config.settings'
ENV UV_NO_DEV=1

# Copy only dependency files first for better caching
COPY pyproject.toml uv.lock README.md ./
RUN mkdir -p /var/www/static/ \
     && mkdir -p /opt/movies_admin/static/ \
     && uv sync --frozen

# Copy the rest of the application
COPY . .

CMD ["sh", "entrypoint.sh"]


