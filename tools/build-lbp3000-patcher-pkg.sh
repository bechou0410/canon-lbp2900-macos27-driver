#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PKGROOT="$ROOT_DIR/patcher_pkg/root"
SCRIPTS="$ROOT_DIR/patcher_pkg/scripts"
DIST="$ROOT_DIR/dist"
PKG="$DIST/CanonLBP2900-macOS27-lbp3000-patcher.pkg"
FILTER="$PKGROOT/usr/libexec/cups/filter/rastertocapt"
BUILT_FILTER="$ROOT_DIR/third_party/captdriver/build/rastertocapt"

mkdir -p "$DIST"

if [ ! -x "$BUILT_FILTER" ]; then
  echo "Missing built filter: $BUILT_FILTER" >&2
  echo "Run ./tools/build-rastertocapt.sh first." >&2
  exit 1
fi
chmod u+w "$FILTER" 2>/dev/null || true
cp -p "$BUILT_FILTER" "$FILTER"
chmod 0555 "$FILTER"

/usr/bin/find "$PKGROOT" "$SCRIPTS" -name '._*' -delete 2>/dev/null || true

COPYFILE_DISABLE=1 /usr/bin/pkgbuild \
  --root "$PKGROOT" \
  --scripts "$SCRIPTS" \
  --identifier "local.lbp2900.macos27.lbp3000-patcher" \
  --version "27.2.4" \
  --install-location "/" \
  "$PKG"

/usr/bin/shasum -a 256 "$PKG"
