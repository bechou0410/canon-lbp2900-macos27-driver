#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PKGROOT="$ROOT_DIR/patcher_pkg/root"
SCRIPTS="$ROOT_DIR/patcher_pkg/scripts"
DIST="$ROOT_DIR/dist"
PKG="$DIST/CanonLBP2900-macOS27-lbp3000-patcher.pkg"
FILTER="$PKGROOT/usr/libexec/cups/filter/rastertocapt"
BUILT_FILTER="$ROOT_DIR/third_party/captdriver/build/rastertocapt"
PPD="$PKGROOT/Library/Printers/PPDs/Contents/Resources/CanonLBP2900-open-capt.ppd"

mkdir -p "$DIST"

if [ ! -x "$BUILT_FILTER" ]; then
  echo "Missing built filter: $BUILT_FILTER" >&2
  echo "Run ./tools/build-rastertocapt.sh first." >&2
  exit 1
fi
chmod u+w "$FILTER" 2>/dev/null || true
cp -p "$BUILT_FILTER" "$FILTER"
chmod 0555 "$FILTER"

PAYLOAD_ROOT="$(mktemp -d)"
PAYLOAD_SCRIPTS="$(mktemp -d)"
cleanup() {
  rm -rf "$PAYLOAD_ROOT" "$PAYLOAD_SCRIPTS"
}
trap cleanup EXIT

mkdir -p "$PAYLOAD_ROOT/usr/libexec/cups/filter"
mkdir -p "$PAYLOAD_ROOT/Library/Printers/PPDs/Contents/Resources"
install -m 0555 "$BUILT_FILTER" "$PAYLOAD_ROOT/usr/libexec/cups/filter/rastertocapt"
install -m 0644 "$PPD" "$PAYLOAD_ROOT/Library/Printers/PPDs/Contents/Resources/CanonLBP2900-open-capt.ppd"
install -m 0755 "$SCRIPTS/preinstall" "$PAYLOAD_SCRIPTS/preinstall"
install -m 0755 "$SCRIPTS/postinstall" "$PAYLOAD_SCRIPTS/postinstall"

/usr/bin/find "$PAYLOAD_ROOT" "$PAYLOAD_SCRIPTS" -name '._*' -delete 2>/dev/null || true
/usr/bin/xattr -cr "$PAYLOAD_ROOT" "$PAYLOAD_SCRIPTS" 2>/dev/null || true

/usr/bin/env COPYFILE_DISABLE=1 COPY_EXTENDED_ATTRIBUTES_DISABLE=1 /usr/bin/pkgbuild \
  --root "$PAYLOAD_ROOT" \
  --scripts "$PAYLOAD_SCRIPTS" \
  --identifier "local.lbp2900.macos27.lbp3000-patcher" \
  --version "27.2.9" \
  --install-location "/" \
  "$PKG"

/usr/bin/shasum -a 256 "$PKG"
