#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT_DIR/third_party/captdriver/src"
OUT_DIR="$ROOT_DIR/third_party/captdriver/build"
OUT="$OUT_DIR/rastertocapt"
TMP_OUT="$(mktemp -t rastertocapt.XXXXXX)"

mkdir -p "$OUT_DIR"
chmod u+w "$OUT" 2>/dev/null || true
rm -f "$OUT"

clang -std=c99 -Wall -Wextra -pedantic -D_DARWIN_C_SOURCE \
  $(cups-config --cflags) \
  -I"$SRC" \
  "$SRC/rastertocapt.c" \
  "$SRC/capt-command.c" \
  "$SRC/capt-status.c" \
  "$SRC/generic-ops.c" \
  "$SRC/printer.c" \
  "$SRC/paper.c" \
  "$SRC/hiscoa-common.c" \
  "$SRC/hiscoa-compress.c" \
  "$SRC/prn_lbp2900.c" \
  $(cups-config --image --libs) \
  -o "$TMP_OUT"

mv "$TMP_OUT" "$OUT"
chmod 0555 "$OUT"
/usr/bin/shasum -a 256 "$OUT"
