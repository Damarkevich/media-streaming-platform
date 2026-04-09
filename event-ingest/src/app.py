from collections.abc import Callable

from api.v1.events import events_bp
from core.config import settings
from core.producer_lifecycle import (
    Producer,
    create_kafka_producer,
    register_producer_shutdown,
)
from flasgger import Swagger
from flask import Flask
from flask_jwt_extended import JWTManager


def create_app(producer_factory: Callable[[], Producer] | None = None) -> Flask:
    """
    Initializes and configures a Flask application with JWT, Swagger, and
    Kafka producer support. Optionally accepts a producer_factory to
    customize Kafka producer creation. Returns the configured Flask app
    instance.
    """
    app = Flask(__name__)

    app.debug = settings.debug
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
                settings.kafka_api_version,
                settings.kafka_acks,
                settings.kafka_retries,
                settings.kafka_request_timeout_ms,
            )
        )
    )()
    app.extensions["kafka_producer"] = producer
    register_producer_shutdown(producer)

    app.register_blueprint(events_bp)

    return app
