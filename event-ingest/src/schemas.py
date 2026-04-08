from marshmallow import EXCLUDE, Schema, fields, validate

EVENT_TYPES = (
    "click",
    "page_view",
    "play_started",
    "play_progressed",
    "play_paused",
    "play_stopped",
    "quality_changed",
    "search_filtered",
)


class ContextSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    device = fields.String(required=False)
    location = fields.String(required=False)
    browser = fields.String(required=False)
    os = fields.String(required=False)


class PayloadSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    movie_id = fields.UUID(required=False)
    position = fields.Integer(required=False)
    page = fields.String(required=False)
    duration = fields.Integer(required=False)
    button_id = fields.String(required=False)
    search_query = fields.String(required=False)


class EventApiSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    event_id = fields.UUID(required=True)
    event_type = fields.String(required=True, validate=validate.OneOf(EVENT_TYPES))
    event_timestamp = fields.Integer(required=True)

    session_id = fields.UUID(required=True)

    context = fields.Nested(ContextSchema, required=True)

    payload = fields.Nested(PayloadSchema, required=True)


event_schema = EventApiSchema()


class EventBatchSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    events = fields.List(
        fields.Raw(),
        required=True,
        validate=validate.Length(min=1, error="Missing 'events' key in input data"),
        error_messages={
            "required": "Missing 'events' key in input data",
            "invalid": "'events' key should be a list",
        },
    )


event_batch_schema = EventBatchSchema()
