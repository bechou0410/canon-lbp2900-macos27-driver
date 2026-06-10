#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PKGROOT="$ROOT_DIR/patcher_pkg/root"
SCRIPTS="$ROOT_DIR/patcher_pkg/scripts"
DIST="$ROOT_DIR/dist"
PKG="$DIST/CanonLBP2900-macOS27-lbp3000-patcher.pkg"

mkdir -p "$DIST"

/usr/bin/find "$PKGROOT" "$SCRIPTS" -name '._*' -delete 2>/dev/null || true

COPYFILE_DISABLE=1 /usr/bin/pkgbuild \
  --root "$PKGROOT" \
  --scripts "$SCRIPTS" \
  --identifier "local.lbp2900.macos27.lbp3000-patcher" \
  --version "27.2.1" \
  --install-location "/" \
  "$PKG"

/usr/bin/shasum -a 256 "$PKG"
