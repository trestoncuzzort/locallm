#!/bin/bash
# chain8.sh — chapter 8 inside the chroot (runs as root outside, crosses in).
set -u
export LFS=/mnt/lfs
LOG=$LFS/sources/log
echo "chain8: waiting for chapter 7"
until grep -q "CHAIN7 COMPLETE" $LOG/chain7.console 2>/dev/null; do sleep 60; done
mountpoint -q $LFS/proc || { echo "chain8: remounting kernel filesystems"; bash -e /home/lfs/book/ch07/03-kernfs.sh > $LOG/ch08-remount.log 2>&1 || true; }
cp -r /home/lfs/overrides/. $LFS/tup-build/overrides/ 2>/dev/null || true
echo "chain8: crossing into chroot for chapter 8 (the long one)"
chroot "$LFS" /usr/bin/env -i \
  HOME=/root TERM="${TERM:-xterm}" PATH=/usr/bin:/usr/sbin \
  MAKEFLAGS=-j$(nproc) LFS= TUP_OVERRIDES=/tup-build/overrides \
  TUP_TESTS="glibc gcc binutils" \
  /bin/bash /tup-build/driver.sh /tup-build/book/ch08 \
  && echo "CHAIN8 COMPLETE" || echo "CHAIN8 FAILED"
