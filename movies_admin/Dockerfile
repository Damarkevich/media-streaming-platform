FROM python:3.14

COPY --from=ghcr.io/astral-sh/uv:0.9.22 /uv /uvx /bin/

WORKDIR /opt/movies_admin

ENV DJANGO_SETTINGS_MODULE 'config.settings'
ENV UV_NO_DEV=1

COPY pyproject.toml uv.lock ./

RUN  mkdir -p /var/www/static/ \
     && mkdir -p /opt/movies_admin/static/ \
     && uv sync --locked

COPY . .

RUN uv run manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "entrypoint.sh"]


