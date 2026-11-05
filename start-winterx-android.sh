#!/bin/sh
# Linux/macOS: start Spring with WinterX on a rooted device (see docs/rooted-android.md). Keep this terminal open.
cd "$(dirname "$0")" || exit 1
exec "${WINTERX_PYTHON:-python3}" tools/rooted_launch.py start "$@"
