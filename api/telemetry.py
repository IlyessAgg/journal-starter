import os

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

endpoint = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://127.0.0.1:4317",
)

tracer = trace.get_tracer("journal-api")

meter = metrics.get_meter("journal-api")
entry_counter = meter.create_counter(
    name="journal.entries.created",
    description="Number of journal entries created",
    unit="1",
)


def setup_telemetry(app: FastAPI) -> None:
    """
    Configure OpenTelemetry tracing for the Journal API.
    """

    resource = Resource.create(
        {
            "service.name": "journal-api",
        }
    )

    tracer_provider = TracerProvider(resource=resource)

    span_exporter = OTLPSpanExporter(
        endpoint=endpoint,
        insecure=True,
    )

    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    metric_exporter = OTLPMetricExporter(
        endpoint=endpoint,
        insecure=True,
    )

    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=5000,  # export every 5 seconds while developing
    )

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )

    metrics.set_meter_provider(meter_provider)

    FastAPIInstrumentor.instrument_app(app)
