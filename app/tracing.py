from contextlib import contextmanager


class NoopSpan:
    """Tiny span shim so route instrumentation stays harmless."""

    def set_attribute(self, *args, **kwargs):
        return None

    def add_event(self, *args, **kwargs):
        return None


class NoopTracer:
    @contextmanager
    def start_as_current_span(self, *_args, **_kwargs):
        yield NoopSpan()


def setup_tracing(_app):
    """Return a no-op tracer; external tracing can be reintroduced later if needed."""
    return NoopTracer()
