"""Respring orchestration for a verified, reversible APK transaction.

Platform callbacks must stop and start only the intended Spring instance. This
module deliberately does not select or control a live Mac.APK installation.
"""
import time
import apk_transaction as transaction


def run(target, patched, state, expected_sha, marker, stop, start, timeout=45, interval=0.25):
    transaction.prepare(target, patched, state, expected_sha)
    # If shutdown fails, do not touch the installed APK.
    stop()
    try:
        transaction.activate(state)
        transaction.prepare_boot(state, marker)
        start()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if transaction.verify_boot(state):
                return {'ok': True, 'message': 'Patched Spring started successfully'}
            time.sleep(interval)
        raise TimeoutError('Patched Spring did not produce a fresh boot receipt')
    except Exception as failure:
        # Do not replace the APK under a running process. If stopping fails,
        # surface the recovery error and leave the journal intact.
        try:
            stop()
            transaction.rollback(state)
            start()
        except Exception as recovery:
            raise RuntimeError('Activation failed: {}; automatic recovery failed: {}'.format(failure, recovery)) from recovery
        return {'ok': False, 'message': 'Activation failed; original Spring was restored: {}'.format(failure)}
