# Canon LBP2900 macOS 27 LBP3000 Patcher

Small patch package for using Canon LBP2900 on macOS 27 after installing Canon's original LBP3000/CAPT driver.

The patcher creates this printer queue:

```text
Canon_LBP2900
```

## Download

Use the latest patcher release:

```text
CanonLBP2900-macOS27-lbp3000-patcher.pkg
```

## Install

1. Install Canon's original LBP3000/CAPT driver first.
2. Connect the Canon LBP2900 by USB and turn it on.
3. Open `CanonLBP2900-macOS27-lbp3000-patcher.pkg`.
4. Complete the macOS Installer steps.
5. Open System Settings > Printers & Scanners and confirm `Canon_LBP2900` exists.
6. Print a test page.

If macOS blocks the unsigned package, right-click the `.pkg`, choose Open, then confirm.

## What The Patcher Does

- Keeps Canon's original LBP3000/CAPT driver files in place.
- Installs the open `rastertocapt` CUPS filter.
- Installs `CanonLBP2900-open-capt.ppd`.
- Removes old conflicting queues named `Canon_LBP2900`, `Canon_LBP2900_Open`, `Canon_LBP2900_2`, `Canon_LBP3000_Status`, and `Canon_LBP3000`.
- Creates and enables a fresh `Canon_LBP2900` USB queue.
- Sets A4 as the default paper size.

## Balanced Speed Mode

The bundled `rastertocapt` filter is tuned for a balance between speed and stability on macOS 27. It still waits for printer status at safe page boundaries, but it drains the USB backend less aggressively while streaming print data. This reduces avoidable USB handshakes without removing the CAPT status checks that keep LBP2900 prints reliable.

## Verify

```sh
lpstat -t
printf 'Canon LBP2900 macOS 27 test\n' >/tmp/lbp2900-test.txt
lp -d Canon_LBP2900 -o PageSize=A4 /tmp/lbp2900-test.txt
```

## Troubleshooting

If the printer appears offline:

```sh
cancel -a Canon_LBP2900
cupsenable Canon_LBP2900
cupsaccept Canon_LBP2900
lpstat -t
```

If CUPS says the job completed but no paper comes out, power-cycle the printer, unplug USB for 10 seconds, reconnect USB, then print again.

Installer log:

```text
/var/tmp/lbp2900-lbp3000-patcher.log
```

## Rebuild

```sh
./tools/build-lbp3000-patcher-pkg.sh
```

This compiles the balanced `rastertocapt` filter from `third_party/captdriver/src`, copies it into the patcher payload, then writes the package to:

```text
dist/CanonLBP2900-macOS27-lbp3000-patcher.pkg
```

## Notes

Canon's proprietary CAPT `capdftopdl` filter returned `unsupportedsize` during macOS 27 testing. This patcher uses the open CAPT raster filter path instead.

## Acknowledgements

Thanks to Codex for assisting with testing, packaging, and release notes.
