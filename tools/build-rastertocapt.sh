#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT_DIR/third_party/captdriver/src"
OUT_DIR="$ROOT_DIR/third_party/captdriver/build"
OUT="$OUT_DIR/rastertocapt"

mkdir -p "$OUT_DIR"

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
  -o "$OUT"

chmod 0555 "$OUT"
/usr/bin/shasum -a 256 "$OUT"
