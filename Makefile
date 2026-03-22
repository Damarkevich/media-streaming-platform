COMPOSE = docker-compose
LOCAL_INFRA_SERVICES = movies-elasticsearch movies-db movies-redis jaeger

.PHONY: dev-infra-up dev-infra-down dev-infra-ps

dev-infra-up:
	$(COMPOSE) up -d $(LOCAL_INFRA_SERVICES)

dev-infra-down:
	$(COMPOSE) stop $(LOCAL_INFRA_SERVICES)

dev-infra-ps:
	$(COMPOSE) ps $(LOCAL_INFRA_SERVICES)