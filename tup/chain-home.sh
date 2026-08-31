#!/bin/bash
# chain-home.sh — chapters 9, 10, 11 inside the chroot; the last leg.
set -u
export LFS=/mnt/lfs
LOG=$LFS/sources/log
echo "chain-home: waiting for chapter 8"
until grep -q "CHAIN8 COMPLETE" $LOG/chain8.console 2>/dev/null; do sleep 120; done
mountpoint -q $LFS/proc || bash -e /home/lfs/book/ch07/03-kernfs.sh > $LOG/home-remount.log 2>&1 || true
cp -r /home/lfs/book/ch09 /home/lfs/book/ch10 /home/lfs/book/ch11 $LFS/tup-build/book/ 2>/dev/null || true
cp -r /home/lfs/overrides/. $LFS/tup-build/overrides/
run_ch() {
  chroot "$LFS" /usr/bin/env -i HOME=/root TERM="${TERM:-xterm}" \
    PATH=/usr/bin:/usr/sbin MAKEFLAGS=-j$(nproc) LFS= \
    TUP_OVERRIDES=/tup-build/overrides \
    /bin/bash /tup-build/driver.sh "/tup-build/book/$1"
}
run_ch ch09 && run_ch ch10 && run_ch ch11 \
  && echo "TUP BUILT — ready for the boot witness" || echo "CHAIN-HOME FAILED"
