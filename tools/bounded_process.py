"""Binary subprocess capture bounded in memory on Windows/POSIX. Never invokes a host shell."""
import subprocess
import threading
import time


class OutputLimitError(OSError):
    pass


def run(command, *, input=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=20, check=False, shell=False, output_limit=24 * 1024 * 1024 + 1,
        error_limit=64 * 1024):
    if shell or stdout != subprocess.PIPE or stderr != subprocess.PIPE:
        raise ValueError('Bounded capture requires binary pipes and no shell')
    if input is not None and (not isinstance(input, bytes) or len(input) > 24 * 1024 * 1024):
        raise ValueError('Subprocess input must be bounded bytes')
    if not 0 < timeout <= 120 or not 0 <= output_limit <= 24 * 1024 * 1024 + 1 or not 0 <= error_limit <= 64 * 1024:
        raise ValueError('Invalid subprocess deadline/output limit')
    process = subprocess.Popen(command, stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    buffers = [bytearray(), bytearray()]
    exceeded = threading.Event()
    errors = []

    def read(pipe, index, limit):
        try:
            while True:
                chunk = pipe.read(64 * 1024)
                if not chunk: break
                remaining = limit - len(buffers[index])
                buffers[index].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    exceeded.set(); break
        except OSError as exc:
            errors.append(exc); exceeded.set()

    def write():
        try:
            process.stdin.write(input); process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass  # A failing/disconnected tool may close its input first.
        finally:
            process.stdin.close()

    threads = [threading.Thread(target=read, args=(process.stdout, 0, output_limit), daemon=True),
               threading.Thread(target=read, args=(process.stderr, 1, error_limit), daemon=True)]
    if input is not None: threads.append(threading.Thread(target=write, daemon=True))
    for thread in threads: thread.start()
    deadline = time.monotonic() + timeout
    timed_out = False
    try:
        while process.poll() is None:
            if exceeded.wait(min(.05, max(0, deadline - time.monotonic()))): break
            if time.monotonic() >= deadline:
                timed_out = True; break
        if process.poll() is None:
            process.kill()
        process.wait()
        for thread in threads: thread.join(timeout=1)
        if any(thread.is_alive() for thread in threads):
            raise OutputLimitError('Subprocess pipes did not close after the deadline')
        if exceeded.is_set():
            raise OutputLimitError('Subprocess output exceeded its bound' if not errors else 'Subprocess capture failed')
        if timed_out:
            raise subprocess.TimeoutExpired(command, timeout, bytes(buffers[0]), bytes(buffers[1]))
        result = subprocess.CompletedProcess(command, process.returncode, bytes(buffers[0]), bytes(buffers[1]))
        if check: result.check_returncode()
        return result
    finally:
        if process.poll() is None:
            process.kill(); process.wait()
        # Close only after readers have stopped; closing a pipe during read can block on Windows.
        if not any(thread.is_alive() for thread in threads):
            process.stdout.close(); process.stderr.close()
