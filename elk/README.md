# ELK setup

This folder contains local development configuration for log collection.

## Components

- Dedicated Elasticsearch node stores only ELK logs and is available on `http://localhost:9201`.
- Filebeat reads Docker JSON logs from `/var/lib/docker/containers`.
- Logstash receives logs on port `5044` and writes to Elasticsearch.
- Kibana visualizes indices in Elasticsearch.

## Expected index pattern

- `docker-logs-*`
- `nginx-logs-*`

## Quick validation

1. Start infra with `make dev-infra-up`.
2. Open Kibana at `http://localhost:5601`.
3. In Kibana, create Data Views: `docker-logs-*` and `nginx-logs-*` and use `@timestamp`.
4. Generate app logs via `docker-compose logs -f movies-auth`.
5. Generate nginx logs by opening any endpoint through nginx, for example `http://localhost/api/content/docs`.
