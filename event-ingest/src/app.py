from collections.abc import Callable

from flasgger import Swagger
from flask import Flask
from flask_jwt_extended import JWTManager

from api.v1.events import events_bp
from core.config import settings
from core.producer_lifecycle import (
    Producer,
    create_kafka_producer,
    register_producer_shutdown,
)


def create_app(producer_factory: Callable[[], Producer] | None = None) -> Flask:
    """
    Initializes and configures a Flask application with JWT, Swagger, and
    Kafka producer support. Optionally accepts a producer_factory to
    customize Kafka producer creation. Returns the configured Flask app
    instance.
    """
    app = Flask(settings.service_name)

    app.config["JWT_SECRET_KEY"] = settings.authjwt_secret_key
    app.config["JWT_ALGORITHM"] = settings.authjwt_algorithm
    app.config["MAX_CONTENT_LENGTH"] = settings.max_content_length
    app.config["SWAGGER"] = {
        "swagger_version": "2.0",
        "title": settings.service_name,
        "description": settings.service_description,
        "version": "0.1.0",
    }

    JWTManager(app)
    Swagger(app)

    producer = (
        producer_factory
        or (lambda: create_kafka_producer(settings.kafka_bootstrap_servers))
    )()
    app.extensions["kafka_producer"] = producer
    register_producer_shutdown(producer)

    app.register_blueprint(events_bp)

    return app


if __name__ == "__main__":
    create_app().run()
