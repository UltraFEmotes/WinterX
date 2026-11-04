#!/bin/bash
cd "$(dirname "$0")" || exit 1
/usr/bin/env python3 tools/prepare_safe_mode.py
printf '\nPress Return to close this window.'
read -r
