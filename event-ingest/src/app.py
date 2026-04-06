from collections.abc import Callable

from flasgger import Swagger
from flask import Flask
from flask_jwt_extended import JWTManager

from api.v1.events import events_bp
from core.config import settings
from core.producer_lifecycle import (
    KafkaApiVersion,
    Producer,
    create_kafka_producer,
    register_producer_shutdown,
)


def _parse_kafka_api_version(version: str) -> KafkaApiVersion:
    """Convert dotted Kafka API version string to a tuple for kafka-python."""
    parts = tuple(int(part) for part in version.split("."))

    if len(parts) == 2:
        return parts

    raise ValueError("KAFKA_API_VERSION must contain two numeric parts")


def create_app(producer_factory: Callable[[], Producer] | None = None) -> Flask:
    """
    Initializes and configures a Flask application with JWT, Swagger, and
    Kafka producer support. Optionally accepts a producer_factory to
    customize Kafka producer creation. Returns the configured Flask app
    instance.
    """
    app = Flask(__name__)

    app.config["JWT_SECRET_KEY"] = settings.authjwt_secret_key
    app.config["JWT_ALGORITHM"] = settings.authjwt_algorithm
    app.config["MAX_CONTENT_LENGTH"] = settings.event_ingest_max_content_length
    app.config["SWAGGER"] = {
        "swagger_version": "2.0",
        "title": settings.event_ingest_service_name,
        "description": settings.event_ingest_service_description,
        "version": "0.1.0",
    }

    JWTManager(app)
    Swagger(app)

    producer = (
        producer_factory
        or (
            lambda: create_kafka_producer(
                settings.kafka_bootstrap_servers,
                _parse_kafka_api_version(settings.kafka_api_version),
            )
        )
    )()
    app.extensions["kafka_producer"] = producer
    register_producer_shutdown(producer)

    app.register_blueprint(events_bp)

    return app


if __name__ == "__main__":
    create_app().run()
