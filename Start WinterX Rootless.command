#!/bin/bash
# WinterX on Android without root: builds "Spring Launcher (WinterX)" from your phone's own Spring and installs it
# beside the original. See docs/rootless-android.md.
cd "$(dirname "$0")" || exit 1
/usr/bin/env python3 tools/rootless_launch.py start "$@"
echo; read -r -p "Press Return to close." _
