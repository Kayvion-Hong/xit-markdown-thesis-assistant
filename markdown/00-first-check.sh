#!/usr/bin/env sh
set -u
cd "$(dirname "$0")"
python3 tools/doctor.py
