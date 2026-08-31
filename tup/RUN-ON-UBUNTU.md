# Run tup on Ubuntu

Verified 2026-08-31 on Ubuntu 24.04: **40 seconds to `tup login:` under pure
TCG emulation** — no KVM, no nested virtualization, no special hardware. On a
host with KVM it is faster; without one it still works, and that claim is
measured, not hoped.

## 1. Install QEMU (the only prerequisite)

```sh
sudo apt-get install qemu-system-arm qemu-efi-aarch64
```

No sudo on the box? QEMU also installs user-local via a conda/micromamba
environment (`micromamba install -c conda-forge qemu`); everything below is
identical except the firmware path.

## 2. Get the image

`tup-0.1-arm64.qcow2` — a compressed qcow2 of the whole system: kernel, GRUB,
the base built from source with a receipt per page, and the agent layer
(Claude Code preinstalled, its exact cost recorded in
`receipts/LAYER-agent-FULL.md`). `SHA256SUMS` ships beside it; check it:

```sh
sha256sum -c SHA256SUMS
```

## 3. Boot it

```sh
qemu-system-aarch64 -machine virt -cpu cortex-a72 -m 2048 -smp 2 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/AAVMF/AAVMF_CODE.fd \
  -drive file=tup-0.1-arm64.qcow2,format=qcow2,if=virtio \
  -nographic
```

On an arm64 host with KVM, add `-accel kvm` and change `-cpu cortex-a72` to
`-cpu host`. On x86_64 (the lab Dell) leave the command exactly as written —
it emulates, and tup's boot is small enough that this is fine.

Log in as `root` (no password on the witness image; set one). To exit QEMU
from `-nographic`: `Ctrl-a x`.

Note what is *not* in that command: no `-kernel`, no `-initrd`, no `-append`.
QEMU provides firmware and a disk, nothing else. Everything that executes
after the firmware hands off — GRUB, kernel, init, the login prompt — comes
off tup's own disk. That is the acceptance test the build was driven toward,
and `receipts/boot-witness-*.txt` records it being met.

## 4. What you are looking at

- `cat /etc/os-release` — NAME="tup"
- `claude --version` — the agent layer; the full file-level cost of installing
  it is `receipts/LAYER-agent-FULL.md` (4,844 files added, 1 modified, and the
  one modification is listed)
- `receipts/` in the repo — a receipt for every one of the 105 book pages the
  system was built from, plus the inventory of every file on the disk

## What this is not, yet

- Not x86_64-native: the image is arm64 and emulates on x86 hosts. A native
  x86_64 build through the same driver and receipts is planned.
- Not verified on VMware/Hyper-V: the kernel carries SATA/e1000 fallbacks that
  should boot there, but nobody has witnessed it. Anything unwitnessed is
  labeled as such — that is the house rule.
