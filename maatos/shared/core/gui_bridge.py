"""Optional transport hooks. CLI remains independent of Qt."""
_handler = None


def install(handler):
    global _handler
    _handler = handler


def emit(kind, **data):
    if _handler is not None:
        _handler(kind, **data)


def enabled():
    return _handler is not None
