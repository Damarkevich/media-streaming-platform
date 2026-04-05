from pathlib import Path

from flasgger import swag_from
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from core.producer_lifecycle import Producer

from services.event_ingest import process_event_batch

events_bp = Blueprint("events", __name__)
EVENT_INGEST_SPEC_PATH = str(Path(__file__).resolve().with_name("event_ingest.yml"))


@events_bp.route("/api/v1/events/", methods=["POST"])
@jwt_required()
@swag_from(EVENT_INGEST_SPEC_PATH)
def event_ingest():
    """Handle authenticated event ingestion requests."""
    kafka_producer: Producer = current_app.extensions["kafka_producer"]
    user_id: str | None = get_jwt_identity()
    data: object = request.get_json()
    response_body, status_code = process_event_batch(data, user_id, kafka_producer)
    return jsonify(response_body), status_code
