"""OpenTelemetry tracer setup helpers."""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from src.core.config import settings

_provider: TracerProvider | None = None


def configure_tracer() -> None:
    """Configure the global OpenTelemetry tracer provider (idempotent)."""
    global _provider  # noqa: PLW0603

    if _provider is not None:
        return

    provider = TracerProvider(
        resource=Resource.create({"service.name": settings.service_name})
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_traces_endpoint))
    )

    if settings.otel_console_export_enabled:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _provider = provider


def shutdown_tracer() -> None:
    """Shutdown the tracer provider and flush pending spans."""
    global _provider  # noqa: PLW0603

    if _provider is None:
        return

    _provider.shutdown()
    _provider = None
