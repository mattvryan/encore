#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

bash scripts/build_app.sh

APP_PATH="dist/Encore.app"
VERSION="$(uv run python -c "from encore import __version__; print(__version__)")"
DMG_PATH="dist/Encore-${VERSION}.dmg"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

cp -R "$APP_PATH" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

rm -f "$DMG_PATH"
hdiutil create \
  -volname "Encore" \
  -srcfolder "$STAGING" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo "Built: $DMG_PATH"
