#!/bin/sh
# Explicit setup after installation. Leaves other queues and default selection alone.
set -eu
PATH=/usr/bin:/bin:/usr/sbin:/sbin
LC_ALL=C
LANG=C
# Keep lpstat's machine-parsed output stable in macOS installer sessions.
SOFTWARE=CanonLBP2900CAPTPatch
export PATH LC_ALL LANG SOFTWARE
QUEUE=Canon_LBP2900_CAPT
SUPPORT='/Library/Application Support/CanonLBP2900CAPTPatch'
fail() { echo "CAPT setup: $*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || fail 'Run with sudo after installing Canon and the patch.'
"$SUPPORT/capt-patch" check
[ -f "$SUPPORT/installed.sha256" ] || fail 'Apply the patch first.'
(cd / && shasum -a 256 -c "$SUPPORT/installed.sha256")
[ "$#" -eq 1 ] || fail 'Supply the exact usb://Canon/LBP2900?serial=... URI from lpinfo -v.'
case "$1" in 'usb://Canon/LBP2900?serial='?*) ;; *) fail 'Expected an LBP2900 USB URI with a serial number.';; esac
URI="cnbma2://localhost:59687/usbSP/${1#usb://}"
if lpstat -v "$QUEUE" >/dev/null 2>&1; then
    [ -f "$SUPPORT/queue-uri" ] || fail 'Queue already exists and is not owned by this setup.'
    [ "$(cat "$SUPPORT/queue-uri")" = "$URI" ] || fail 'Queue belongs to another device.'
    [ "$(lpstat -v "$QUEUE")" = "device for $QUEUE: $URI" ] || fail 'Queue URI changed; inspect it before reconfiguring.'
    [ -z "$(lpstat -o "$QUEUE")" ] || fail 'Finish or cancel pending jobs first.'
fi
lpadmin -p "$QUEUE" -v "$URI" -P /Library/Printers/PPDs/Contents/Resources/CNMC2LBP2900AUK.ppd.gz -D 'Canon LBP2900 CAPT' -E -o printer-is-shared=false -o printer-error-policy=stop-printer
printf '%s\n' "$URI" > "$SUPPORT/queue-uri"
chmod 600 "$SUPPORT/queue-uri"
# Old community patches may leave a per-user launchctl disabled override even
# after the official LaunchAgent file is restored. The native pipeline needs it.
console_uid=$(/usr/bin/stat -f %u /dev/console)
if [ "$console_uid" -ge 500 ]; then
    service="gui/$console_uid/jp.co.canon.CUPSCAPT2.BackGrounder"
    /bin/launchctl enable "$service"
    if ! /bin/launchctl print "$service" >/dev/null 2>&1; then
        /bin/launchctl bootstrap "gui/$console_uid" /Library/LaunchAgents/jp.co.canon.CUPSCAPT2.BG.plist
    fi
else
    echo 'No desktop user is signed in. Sign in to start Canon BackGrounder.'
fi
echo "Created $QUEUE. Use Canon StatusMonitor and macOS Print Center to test it."
