#!/bin/sh
# WinterX on Android without root (Linux). See docs/rootless-android.md.
cd "$(dirname "$0")" || exit 1
exec "${WINTERX_PYTHON:-python3}" tools/rootless_launch.py start "$@"
