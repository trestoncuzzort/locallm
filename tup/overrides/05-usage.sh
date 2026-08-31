#!/bin/bash
# OVERRIDE ch09/06-usage: the book's bootscript config, byte for byte, plus
# ONE addition tup needs — an agetty on ttyAMA0. tup boots under QEMU with
# console=ttyAMA0, so without this line the system comes up correctly and
# offers a login prompt on virtual consoles nobody can see. The boot witness
# is a login prompt on the serial console; this is the line that produces it.
set -e
PAGE=""
for cand in /tup-build/book/ch09/05-usage.sh /home/lfs/book/ch09/05-usage.sh; do
  [ -s "$cand" ] && { PAGE="$cand"; break; }
done
[ -n "$PAGE" ] || { echo "override: cannot find the usage page"; exit 1; }
sed 's|^1:2345:respawn:/sbin/agetty --noclear tty1 9600$|S0:2345:respawn:/sbin/agetty --noclear ttyAMA0 115200 vt100\n1:2345:respawn:/sbin/agetty --noclear tty1 9600|' \
  "$PAGE" | bash -e
