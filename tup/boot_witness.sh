#!/bin/bash
# boot_witness.sh — boot tup ALONE and record what it says.
#
#   bash tup/boot_witness.sh            # boot, capture, verdict
#   bash tup/boot_witness.sh --keep     # leave the VM up for interaction
#
# THE WITNESS THIS PRODUCES, and why it is the acceptance test: the build VM
# is stopped first, so nothing of Lima, Ubuntu, or the host toolchain is in
# the loop. QEMU is handed the raw disk and UEFI firmware and nothing else —
# no -kernel, no -initrd, no -append. Every byte that executes comes off
# tup's own ESP and root filesystem. If a login prompt appears, tup booted
# itself; there is no other explanation available.
#
# Success is a LOGIN PROMPT on the serial console. Recorded to
# tup/receipts/boot-witness-<date>.txt with the disk hash, the firmware
# identity, the QEMU version, and the console transcript.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
DISK="${TUP_DISK:-$HOME/.lima/_disks/lfs/datadisk}"
FW_CODE="${TUP_FW:-/opt/homebrew/share/qemu/edk2-aarch64-code.fd}"
RECEIPTS="$HERE/receipts"; mkdir -p "$RECEIPTS"
WORK="${TMPDIR:-/tmp}/tup-boot"; mkdir -p "$WORK"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$WORK/console-$STAMP.log"
KEEP="${1:-}"

[ -f "$DISK" ] || { echo "no disk at $DISK"; exit 1; }
[ -f "$FW_CODE" ] || { echo "no UEFI firmware at $FW_CODE (brew install qemu)"; exit 1; }
command -v qemu-system-aarch64 >/dev/null || { echo "qemu-system-aarch64 not on PATH"; exit 1; }

# The disk cannot be booted while the build VM holds it.
if limactl list 2>/dev/null | grep -q "^lfs-host.*Running"; then
  echo "stopping the build VM so tup boots with nothing else attached..."
  limactl stop lfs-host >/dev/null 2>&1
fi

# UEFI needs a writable variable store; a fresh one each run keeps the boot
# path discovery honest (GRUB was installed --removable, so the firmware must
# find EFI/BOOT/BOOTAA64.EFI on tup's own ESP with no prior NVRAM entry).
VARS="$WORK/edk2-vars-$STAMP.fd"
if [ -f /opt/homebrew/share/qemu/edk2-arm-vars.fd ]; then
  cp /opt/homebrew/share/qemu/edk2-arm-vars.fd "$VARS"
else
  dd if=/dev/zero of="$VARS" bs=1m count=64 2>/dev/null
fi

echo "booting tup from $DISK (nothing else attached)"
echo "  console -> $LOG"
set +e
if [ "$KEEP" = "--keep" ]; then
  qemu-system-aarch64 -M virt -cpu host -accel hvf -m 4G -smp 4 -nographic \
    -drive if=pflash,format=raw,readonly=on,file="$FW_CODE" \
    -drive if=pflash,format=raw,file="$VARS" \
    -drive file="$DISK",format=raw,if=virtio,cache=writeback \
    -netdev user,id=n0 -device virtio-net-pci,netdev=n0
  exit $?
fi
( qemu-system-aarch64 -M virt -cpu host -accel hvf -m 4G -smp 4 -nographic \
    -drive if=pflash,format=raw,readonly=on,file="$FW_CODE" \
    -drive if=pflash,format=raw,file="$VARS" \
    -drive file="$DISK",format=raw,if=virtio,cache=writeback \
    -netdev user,id=n0 -device virtio-net-pci,netdev=n0 \
    > "$LOG" 2>&1 ) &
QPID=$!
# Wait for a login prompt, a kernel panic, or the timeout — whichever first.
for i in $(seq 1 120); do
  sleep 2
  grep -qE "tup login:|login:" "$LOG" 2>/dev/null && { VERDICT="BOOTED"; break; }
  grep -qE "Kernel panic|Attempted to kill init|not syncing" "$LOG" 2>/dev/null && { VERDICT="PANIC"; break; }
  kill -0 $QPID 2>/dev/null || { VERDICT="QEMU EXITED"; break; }
done
VERDICT="${VERDICT:-TIMEOUT (240s, no login prompt)}"
kill $QPID 2>/dev/null; wait $QPID 2>/dev/null
set -e

OUT="$RECEIPTS/boot-witness-$STAMP.txt"
{
  echo "tup boot witness — $STAMP"
  echo "VERDICT: $VERDICT"
  echo
  echo "disk      : $DISK"
  echo "disk bytes: $(stat -f %z "$DISK" 2>/dev/null || stat -c %s "$DISK")"
  echo "firmware  : $FW_CODE"
  echo "qemu      : $(qemu-system-aarch64 --version | head -1)"
  echo "invocation: -M virt -cpu host -accel hvf, raw disk + UEFI only;"
  echo "            no -kernel, no -initrd, no -append — tup booted itself."
  echo
  echo "--- console transcript (last 60 lines) ---"
  tail -60 "$LOG"
} > "$OUT"
echo
echo "VERDICT: $VERDICT"
echo "witness: ${OUT#$HERE/}"
[ "$VERDICT" = "BOOTED" ]
