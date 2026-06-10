#!/bin/bash
set -u

LOG="/var/tmp/lbp2900-clean-canon-drivers.log"
exec >>"$LOG" 2>&1

echo "==== $(date) clean Canon printer drivers ===="

/usr/bin/pkill -x StatusMonitor 2>/dev/null || true
/usr/bin/pkill -x "Canon CAPT BackGrounder" 2>/dev/null || true
/usr/bin/pkill -x ccpd 2>/dev/null || true

if /usr/bin/lpstat -e >/dev/null 2>&1; then
  /usr/bin/lpstat -e | while IFS= read -r queue; do
    case "$queue" in
      Canon*|*Canon*|*LBP*)
        echo "Removing queue: $queue"
        /usr/bin/cancel -a "$queue" 2>/dev/null || true
        /usr/sbin/lpadmin -x "$queue" 2>/dev/null || true
        ;;
    esac
  done
fi

for queue in \
  Canon_LBP2900 \
  Canon_LBP2900_Open \
  Canon_LBP2900_2 \
  Canon_LBP3000_Status \
  Canon_LBP3000; do
  /usr/bin/cancel -a "$queue" 2>/dev/null || true
  /usr/sbin/lpadmin -x "$queue" 2>/dev/null || true
done

/bin/rm -rf /Library/Printers/Canon
/bin/rm -rf /Library/Printers/PPDs/Contents/Resources/CNMC2LBP*.ppd.gz
/bin/rm -f /Library/Printers/PPDs/Contents/Resources/CanonLBP2900-*.ppd
/bin/rm -f /Library/Printers/PPDs/Contents/Resources/CanonLBP3000-*.ppd
/bin/rm -f /usr/libexec/cups/filter/rastertocapt
/bin/rm -f /etc/cups/ppd/Canon*.ppd /etc/cups/ppd/*LBP*.ppd 2>/dev/null || true

if /usr/sbin/pkgutil --pkgs >/dev/null 2>&1; then
  /usr/sbin/pkgutil --pkgs | /usr/bin/awk 'tolower($0) ~ /(canon|capt|lbp2900|lbp3000|lbp)/ {print}' | while IFS= read -r receipt; do
    echo "Forgetting receipt: $receipt"
    /usr/sbin/pkgutil --forget "$receipt" 2>/dev/null || true
  done
fi

CURRENT_USER="$(/usr/bin/stat -f %Su /dev/console 2>/dev/null || true)"
CURRENT_UID="$(/usr/bin/stat -f %u /dev/console 2>/dev/null || echo 0)"
if [ -n "$CURRENT_USER" ] && [ "$CURRENT_USER" != "root" ] && [ "$CURRENT_UID" != "0" ]; then
  USER_HOME="$(/usr/bin/dscl . -read "/Users/$CURRENT_USER" NFSHomeDirectory 2>/dev/null | /usr/bin/awk '{print $2}')"
  if [ -n "$USER_HOME" ]; then
    /bin/launchctl asuser "$CURRENT_UID" /usr/bin/sudo -u "$CURRENT_USER" /usr/bin/defaults delete jp.co.canon.CUPSCAPT2.StatusMonitor 2>/dev/null || true
    /bin/rm -rf "$USER_HOME/Library/Saved Application State/jp.co.canon.CUPSCAPT2.StatusMonitor.savedState"
  fi
fi

/bin/launchctl kickstart -k system/org.cups.cupsd 2>/dev/null || true

echo "Remaining Canon queues:"
/usr/bin/lpstat -e 2>/dev/null | /usr/bin/awk 'tolower($0) ~ /(canon|lbp)/ {print}' || true
echo "Remaining Canon printer files:"
/usr/bin/find /Library/Printers -maxdepth 4 \( -path '*Canon*' -o -path '*LBP*' \) -print 2>/dev/null | /usr/bin/head -100 || true
echo "==== clean done ===="

exit 0
