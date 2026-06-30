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
3. Add the printer once as Canon LBP3000/CAPT if macOS does not create a `Canon_LBP3000` queue automatically.
4. Open `CanonLBP2900-macOS27-lbp3000-patcher.pkg`.
5. Complete the macOS Installer steps.
6. Open System Settings > Printers & Scanners and confirm the patched `Canon_LBP2900` queue exists. The original `Canon_LBP3000` queue is left untouched if you created it.
7. Print from `Canon_LBP2900`.

If macOS blocks the unsigned package, right-click the `.pkg`, choose Open, then confirm.

## What The Patcher Does

- Keeps Canon's original LBP3000/CAPT driver files and queue in place.
- Installs the open `rastertocapt` CUPS filter.
- Installs `CanonLBP2900-open-capt.ppd` as the active LBP2900 print PPD.
- Clones the existing `Canon_LBP3000` PPD when present, or Canon's installed `CNMC2LBP3000AUK.ppd.gz` resource otherwise, and saves it as a reference PPD.
- Uses Canon's LBP3000/CAPT install as the runtime source, but keeps the LBP2900 queue on the open `rastertocapt` print path.
- Removes old conflicting LBP2900 patch queues, but does not remove `Canon_LBP3000`.
- Creates and enables a fresh `Canon_LBP2900` USB queue.
- Shows the printer as `Canon LBP2900` without adding `CAPT` to the visible model/description.
- Sets A4 as the default paper size.
- Sets `printer-error-policy=stop-printer` so failed jobs stay visible instead of disappearing from the active print session.
- Reports no-paper/page-output status to CUPS, holds the active job, and stops the printer queue so later jobs cannot run until the user resumes printing.
- Disables Canon CAPT BackGrounder by backing up its LaunchAgent to `jp.co.canon.CUPSCAPT2.BG.plist.disabled-by-lbp2900-patcher`, so it cannot restart after reboot and rewrite the patched queue from `usb://...` to `cnbma2://...`.

## Balanced Speed Mode

The bundled `rastertocapt` filter is tuned for multi-page stability on macOS 27. It waits for the printer to confirm page-out and page-completed status, with conservative safe handoff delays before moving to the next page or ending the job. If the printer reports no paper, the filter reports `media-empty` to CUPS, holds the current job, stops the printer queue, and lets the user resume printing from Print Center after loading paper.

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

If a bad file or filter failure stops the queue, the failed job is intentionally kept visible. Fix or cancel the failed job, then re-enable the queue:

```sh
cupsenable Canon_LBP2900
cupsaccept Canon_LBP2900
```

If `lpstat -t` shows `Canon_LBP2900` using a `cnbma2://.../usbSP/...` device URI, rerun the patcher. The working LBP2900 queue should use a direct `usb://Canon/LBP2900...` URI. On v27.2.9 and newer, the patcher also disables Canon CAPT BackGrounder persistently so this should not come back after reboot.

If CUPS says the job completed but no paper comes out, power-cycle the printer, unplug USB for 10 seconds, reconnect USB, then print again.

The patcher requires Canon's original LBP3000/CAPT driver as a source for runtime and PPD files under:

```text
/Library/Printers/Canon/CUPSCAPT2
```

The patcher does not include those Canon proprietary runtime files.

Installer log:

```text
/var/tmp/lbp2900-lbp3000-patcher.log
```

## Rebuild

```sh
./tools/build-rastertocapt.sh
./tools/build-lbp3000-patcher-pkg.sh
```

This compiles the balanced `rastertocapt` filter from `third_party/captdriver/src`, copies it into the patcher payload, then writes the package to:

```text
dist/CanonLBP2900-macOS27-lbp3000-patcher.pkg
```

## Notes

Canon's proprietary CAPT `capdftopdl` filter returned `unsupportedsize` during macOS 27 testing. This patcher uses the open CAPT raster filter path instead.

During macOS 27 testing, a full LBP3000 PPD clone could leave CUPS stuck at "sending data to printer" when paired with `rastertocapt`. The patcher still uses the installed LBP3000/CAPT driver as the Canon runtime source, but the active LBP2900 queue intentionally uses the open CAPT PPD.

## Acknowledgements

Thanks to Codex for assisting with testing, packaging, and release notes.
