"""Local lifecycle/crash diagnostics; never records chat or model prompts."""
import atexit
from datetime import datetime
import faulthandler
import logging
import os
import platform
from pathlib import Path
import sys
import threading
import traceback

_logger = logging.getLogger('maat.gui.lifecycle')
_logger.addHandler(logging.NullHandler())
_stream = None  # Keep the native fault handler's descriptor alive until process exit.


def event(name, **fields):
    _logger.info('%s %s', name, ' '.join(f'{key}={value!r}' for key, value in fields.items()))


def exception(name):
    """Record the current traceback without serializing local variables."""
    _logger.exception(name)


def failure(name, error):
    """Record error type and call sites, excluding messages and local variables.

    Handled command/thread errors can contain private user input in their
    exception message; file, function and line still let us locate the defect.
    """
    frames = traceback.extract_tb(error.__traceback__, limit=25)
    locations = '\n'.join(f'  {frame.filename}:{frame.lineno} in {frame.name}' for frame in frames)
    _logger.error('%s error_type=%s\n%s', name, type(error).__name__, locations)


def configure(role='gui', *, announce=True):
    global _stream
    if _stream is not None:
        return Path(_stream.name)
    from apps.maat_rpg.session_shared import BASE_APP_SUPPORT_DIR
    try:
        folder = Path(os.environ.get('MAAT_GUI_DATA_ROOT') or BASE_APP_SUPPORT_DIR) / 'logs'
        folder.mkdir(parents=True, exist_ok=True)
        role = 'worker' if role == 'worker' else 'gui'
        path = folder / f'{role}-{datetime.now():%Y%m%d-%H%M%S}-{os.getpid()}.log'
        _stream = path.open('a', encoding='utf-8', buffering=1)
    except OSError:
        return None  # Diagnostics must never prevent starting the game.
    handler = logging.StreamHandler(_stream)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False
    faulthandler.enable(file=_stream, all_threads=True)
    previous_hook = sys.excepthook

    def report_exception(kind, exception, traceback):
        _logger.error('Unhandled %s exception', role, exc_info=(kind, exception, traceback))
        previous_hook(kind, exception, traceback)

    sys.excepthook = report_exception
    previous_thread_hook = threading.excepthook
    previous_unraisable_hook = sys.unraisablehook

    def report_thread_exception(args):
        failure('thread_failed', args.exc_value)
        previous_thread_hook(args)

    def report_unraisable(args):
        if args.exc_value is not None:
            failure('cleanup_callback_failed', args.exc_value)
        previous_unraisable_hook(args)

    threading.excepthook = report_thread_exception
    sys.unraisablehook = report_unraisable
    atexit.register(lambda: event('python_exit'))
    event('startup', role=role, pid=os.getpid(), python=sys.version.split()[0],
          platform=sys.platform, machine=platform.machine(), cpu_variant=os.environ.get('MAAT_CPU_VARIANT', 'default'))
    if announce:
        print(f'MAAT Diagnoseprotokoll: {path}', file=sys.stderr, flush=True)
    return path
