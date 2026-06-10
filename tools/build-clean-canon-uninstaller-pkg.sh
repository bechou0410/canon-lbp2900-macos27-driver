#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT_DIR/dist"
PKG="$DIST/Canon-CAPT-clean-uninstall-local.pkg"
SCRIPT_SRC="$ROOT_DIR/tools/clean-canon-drivers.sh"

mkdir -p "$DIST"

SCRIPTS="$(mktemp -d)"
PAYLOAD="$(mktemp -d)"
cleanup() {
  rm -rf "$SCRIPTS" "$PAYLOAD"
}
trap cleanup EXIT

install -m 0755 "$SCRIPT_SRC" "$SCRIPTS/postinstall"

COPYFILE_DISABLE=1 /usr/bin/pkgbuild \
  --root "$PAYLOAD" \
  --scripts "$SCRIPTS" \
  --identifier "local.lbp2900.clean-canon-uninstall" \
  --version "1.0.0" \
  --install-location "/" \
  "$PKG"

/usr/bin/shasum -a 256 "$PKG"
