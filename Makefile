COMPOSE = docker-compose
LOCAL_INFRA_SERVICES = movies-elasticsearch elk-elasticsearch movies-db movies-redis jaeger kibana logstash filebeat kafka-0 kafka-1 kafka-2 kafka-ui zookeeper clickhouse-node1 clickhouse-node2 clickhouse-node3 clickhouse-node4

.PHONY: dev-infra-up dev-infra-down dev-infra-ps

dev-infra-up:
	$(COMPOSE) up -d $(LOCAL_INFRA_SERVICES)

dev-infra-down:
	$(COMPOSE) stop $(LOCAL_INFRA_SERVICES)

dev-infra-ps:
	$(COMPOSE) ps $(LOCAL_INFRA_SERVICES)