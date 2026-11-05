#!/bin/bash
# macOS: start Spring with WinterX on a rooted device or emulator (see docs/rooted-android.md).
# Keep this window open while using Ruby. Pick a device with WINTERX_SERIAL when several are connected.
cd "$(dirname "$0")" || exit 1
PY="${WINTERX_PYTHON:-}"
LOCAL_FRIDA=""
if [ -z "$PY" ]; then if [ -x "$LOCAL_FRIDA" ]; then PY="$LOCAL_FRIDA"; else PY=python3; fi; fi
"$PY" tools/rooted_launch.py start "$@"
printf '\nPress Return to close this window.'
read -r
