# This file will contain shared dependencies like database sessions
# For now it's mostly a placeholder

def get_tracer():
    """
    Returns the global tracer instance.
    This will be useful when we need the tracer in other modules.
    """
    from opentelemetry import trace
    return trace.get_tracer(__name__)
