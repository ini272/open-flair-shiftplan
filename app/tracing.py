from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Set up OpenTelemetry with Jaeger exporter
# This configures where and how our tracing data will be sent
def setup_tracing(app):
    resource = Resource(attributes={
        SERVICE_NAME: "fastapi-tracing-demo"  # This name will appear in the Jaeger UI
    })

    # Configure the Jaeger exporter to send traces to the Jaeger service
    # The host name "jaeger" matches the service name in docker-compose.yml
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",  # Service name in docker-compose
        agent_port=6831,  # Default Jaeger agent port for Thrift protocol
    )

    # Set up the tracer provider with our resource information
    provider = TracerProvider(resource=resource)

    # BatchSpanProcessor collects spans and sends them in batches to the exporter
    processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(processor)

    # Set the global tracer provider
    trace.set_tracer_provider(provider)

    # Instrument FastAPI with OpenTelemetry
    # This automatically creates spans for all requests
    FastAPIInstrumentor.instrument_app(app)
    
    return trace.get_tracer(__name__)
