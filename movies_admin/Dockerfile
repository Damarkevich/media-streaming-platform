FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.22 /uv /uvx /bin/

WORKDIR /opt/movies_admin

ENV DJANGO_SETTINGS_MODULE 'config.settings'
ENV UV_NO_DEV=1

COPY pyproject.toml uv.lock ./

RUN  mkdir -p /var/www/static/ \
     && mkdir -p /opt/movies_admin/static/ \
     && uv sync --frozen --no-cache

COPY . .

RUN uv run manage.py collectstatic --noinput

CMD ["sh", "entrypoint.sh"]


