"""Start a patched Spring overlay and verify its startup, with rollback.

Platform callbacks must ensure the original and patched apps never run at the
same time. This module does not choose or control an actual running app.
"""
from pathlib import Path
import time


def run(marker, stop_original, start_patched, stop_patched, start_original,
        healthy=lambda: True, before_start=lambda: None, timeout=45, interval=.25,
        stability=3, success_message='Successfully Jailbroken', fallback_name='original Spring'):
    marker = Path(marker)
    if marker.name != 'boot-ok-v1' or marker.parent.name != 'ruby' or marker.is_symlink():
        raise ValueError('Unexpected boot marker path')
    # No mutation before a successful graceful shutdown of the original.
    stop_original()
    try:
        before_start()
        marker.unlink(missing_ok=True)
        start_patched()
        deadline = time.monotonic() + timeout
        first_receipt = None
        while time.monotonic() < deadline:
            if not healthy():
                raise RuntimeError('Patched Spring exited during startup')
            if not marker.is_symlink() and marker.is_file():
                if first_receipt is None:
                    first_receipt = time.monotonic()
                if time.monotonic() - first_receipt >= stability:
                    return {'ok': True, 'message': success_message}
            time.sleep(interval)
        raise TimeoutError('Patched Spring did not produce a fresh boot receipt')
    except Exception as failure:
        try:
            stop_patched()
            start_original()
        except Exception as recovery:
            raise RuntimeError('Operation failed: {}; {} could not be restarted: {}'.format(failure, fallback_name, recovery)) from recovery
        return {'ok': False, 'message': 'Operation failed; {} was restarted: {}'.format(fallback_name, failure)}
