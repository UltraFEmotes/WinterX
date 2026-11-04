"""Process locks using only the standard library on Windows, Linux and macOS."""
from contextlib import contextmanager
import errno
import os
from pathlib import Path
import time


@contextmanager
def exclusive_lock(path, timeout=30):
    """Lock one persistent byte; never delete a lock file another process uses."""
    if timeout < 0:
        raise ValueError('Lock timeout cannot be negative')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('Lock file must not be a symlink')
    with path.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            # Windows byte-range locks need a byte even in a newly created file.
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b'\0')
                handle.flush()

            def acquire():
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

            def release():
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            def acquire():
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            def release():
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        deadline = time.monotonic() + timeout
        while True:
            try:
                acquire()
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError('Another bridge/package operation holds ' + str(path)) from exc
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            release()
