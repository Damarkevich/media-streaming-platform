COMPOSE = docker-compose
LOCAL_INFRA_SERVICES = movies-elasticsearch elk-elasticsearch movies-db movies-redis movies-mongodb jaeger kibana logstash filebeat kafka-0 kafka-1 kafka-2 kafka-ui zookeeper clickhouse-node1 clickhouse-node2 clickhouse-node3 clickhouse-node4 sentry-db glitchtip glitchtip-worker
SQLITE_TO_POSTGRES_DIR = sqlite_to_postgres
SQLITE_TO_POSTGRES_RECIPIENT_DB_USER ?= postgres
SQLITE_TO_POSTGRES_RECIPIENT_DB_PASSWORD ?= $(shell sed -n 's/^POSTGRES_PASSWORD=//p' .env 2>/dev/null | head -n 1 | tr -d '\r')
SQLITE_TO_POSTGRES_RECIPIENT_DB_HOST ?= 127.0.0.1
SQLITE_TO_POSTGRES_RECIPIENT_DB_PORT ?= 5432

.PHONY: dev-infra-up dev-infra-down dev-infra-ps sqlite-to-postgres-check-env sqlite-to-postgres-wait-db sqlite-to-postgres-load

dev-infra-up:
	$(COMPOSE) up -d $(LOCAL_INFRA_SERVICES)
	$(MAKE) sqlite-to-postgres-load

dev-infra-down:
	$(COMPOSE) stop $(LOCAL_INFRA_SERVICES)

dev-infra-ps:
	$(COMPOSE) ps $(LOCAL_INFRA_SERVICES)

sqlite-to-postgres-load:
	$(MAKE) sqlite-to-postgres-check-env
	$(MAKE) sqlite-to-postgres-wait-db
	cd $(SQLITE_TO_POSTGRES_DIR) && env -u VIRTUAL_ENV \
		RECIPIENT_DB_USER=$(SQLITE_TO_POSTGRES_RECIPIENT_DB_USER) \
		RECIPIENT_DB_PASSWORD=$(SQLITE_TO_POSTGRES_RECIPIENT_DB_PASSWORD) \
		RECIPIENT_DB_HOST=$(SQLITE_TO_POSTGRES_RECIPIENT_DB_HOST) \
		RECIPIENT_DB_PORT=$(SQLITE_TO_POSTGRES_RECIPIENT_DB_PORT) \
		uv run python main.py

sqlite-to-postgres-check-env:
	@test -n "$(SQLITE_TO_POSTGRES_RECIPIENT_DB_PASSWORD)" || ( \
		echo "SQLITE_TO_POSTGRES_RECIPIENT_DB_PASSWORD is not set." >&2; \
		echo "Set POSTGRES_PASSWORD in .env or pass SQLITE_TO_POSTGRES_RECIPIENT_DB_PASSWORD explicitly." >&2; \
		echo "Usage: make dev-infra-up SQLITE_TO_POSTGRES_RECIPIENT_DB_PASSWORD=<password>" >&2; \
		exit 1 \
	)

sqlite-to-postgres-wait-db:
	cd $(SQLITE_TO_POSTGRES_DIR) && env -u VIRTUAL_ENV \
		RECIPIENT_DB_USER=$(SQLITE_TO_POSTGRES_RECIPIENT_DB_USER) \
		RECIPIENT_DB_PASSWORD=$(SQLITE_TO_POSTGRES_RECIPIENT_DB_PASSWORD) \
		RECIPIENT_DB_HOST=$(SQLITE_TO_POSTGRES_RECIPIENT_DB_HOST) \
		RECIPIENT_DB_PORT=$(SQLITE_TO_POSTGRES_RECIPIENT_DB_PORT) \
		sh -c 'i=0; \
		while [ $$i -lt 30 ]; do \
			uv run python -c "import os, psycopg; psycopg.connect(dbname=os.getenv(\"RECIPIENT_DB_NAME\", \"movies_database\"), user=os.environ[\"RECIPIENT_DB_USER\"], password=os.environ[\"RECIPIENT_DB_PASSWORD\"], host=os.environ[\"RECIPIENT_DB_HOST\"], port=os.environ[\"RECIPIENT_DB_PORT\"], options=\"-c search_path=content\").close()" >/dev/null 2>&1 && echo "Postgres is ready for sqlite_to_postgres" && exit 0; \
			i=$$((i + 1)); \
			sleep 1; \
		done; \
		echo "Postgres is not ready after 30 seconds" >&2; \
		exit 1'
