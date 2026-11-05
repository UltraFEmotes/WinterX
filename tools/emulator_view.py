#!/usr/bin/env python3
"""Read-only, loopback live HTML viewer for an explicitly selected disposable emulator."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import json
import secrets
import struct
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--control', action='store_true', help='Allow the user to tap/swipe the disposable emulator from this local page')
    args = parser.parse_args()
    if not re.fullmatch(r'emulator-[0-9]{4,5}', args.serial):
        raise ValueError('Select an explicit emulator serial')
    if not 1024 <= args.port <= 65535:
        raise ValueError('Invalid viewer port')
    lock = threading.Lock()
    control_lock = threading.Lock()
    token = secrets.token_hex(32) if args.control else ''
    cached, observed = b'', 0.0

    def frame():
        nonlocal cached, observed
        with lock:
            if cached and time.monotonic() - observed < .6:
                return cached
            result = subprocess.run([args.adb, '-s', args.serial, 'exec-out', 'screencap', '-p'],
                                    capture_output=True, timeout=10, check=True)
            if not result.stdout.startswith(b'\x89PNG\r\n\x1a\n') or len(result.stdout) > 16 * 1024 * 1024:
                raise ValueError('Invalid bounded screenshot')
            cached, observed = result.stdout, time.monotonic()
            return cached

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                if self.path == '/' or self.path.startswith('/index'):
                    payload, kind = (ROOT / 'Emulator Live View.html').read_bytes(), 'text/html; charset=utf-8'
                    payload = payload.replace(b'__CONTROL_TOKEN__', token.encode())
                elif self.path.split('?', 1)[0] == '/frame':
                    payload, kind = frame(), 'image/png'
                else:
                    self.send_error(404); return
                self.send_response(200)
                self.send_header('Content-Type', kind)
                self.send_header('Content-Length', str(len(payload)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers(); self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                self.send_error(503, 'Emulator feed unavailable')

        def do_POST(self):
            origin = 'http://127.0.0.1:' + str(args.port)
            if not args.control or self.path != '/input' or self.headers.get('Origin') != origin or not secrets.compare_digest(self.headers.get('X-WinterX-Control', ''), token):
                self.send_error(403); return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2048: raise ValueError('Invalid input size')
                value = json.loads(self.rfile.read(length))
                action = value.get('action')
                if action in ('tap', 'swipe'):
                    width, height = struct.unpack('>II', frame()[16:24])
                    keys = ('x', 'y') if action == 'tap' else ('x', 'y', 'x2', 'y2')
                    coordinates = []
                    for index, key in enumerate(keys):
                        item = value.get(key)
                        if not isinstance(item, int) or not 0 <= item < (width if index % 2 == 0 else height): raise ValueError('Invalid coordinates')
                        coordinates.append(str(item))
                    command = ['input', action, *coordinates]
                    if action == 'swipe': command.append('350')
                elif action == 'key' and value.get('key') in ('back', 'enter', 'delete'):
                    command = ['input', 'keyevent', {'back': '4', 'enter': '66', 'delete': '67'}[value['key']]]
                else: raise ValueError('Unsupported input')
                with control_lock:
                    subprocess.run([args.adb, '-s', args.serial, 'shell', *command], capture_output=True, timeout=10, check=True)
                self.send_response(204); self.end_headers()
            except Exception:
                self.send_error(400, 'Emulator input was refused')

        def log_message(self, *arguments):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print('Live emulator viewer: http://127.0.0.1:' + str(args.port), flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
