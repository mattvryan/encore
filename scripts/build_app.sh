#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --all-groups
uv run python setup_app.py py2app
echo "Built: dist/Encore.app"
