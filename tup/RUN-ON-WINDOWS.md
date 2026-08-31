# Run tup on a Windows PC

tup 0.1 is arm64. A Windows lab machine is almost certainly x86_64, and that
rules out the tools you'd reach for first: **VMware Workstation, VirtualBox,
and Hyper-V cannot run an arm64 guest on an x86 host** — they virtualize the
CPU they're on, they don't emulate a different one. The `.vmdk`/`.vdi` files
in the release are for arm hosts and for the future x86_64 tup; on this PC
they will not boot, and that is expected, not a bug.

What does work is **QEMU**, which emulates the CPU. tup's boot is small
enough that emulation is fine — measured at 40 seconds to a login prompt on
an Ubuntu host with no acceleration at all. A Windows boot under the same
TCG emulation has not been witnessed yet; you would be the first, and the
witness is worth recording (see the end).

## What to bring

- `tup-0.1-arm64.qcow2` (~2.3 GB) and `SHA256SUMS`, copied from the release
  directory (USB stick is fine).

Verify the copy survived the trip — PowerShell:

```powershell
Get-FileHash .\tup-0.1-arm64.qcow2 -Algorithm SHA256
# compare against the line in SHA256SUMS
```

## Path A — QEMU for Windows (native)

1. Install QEMU from https://qemu.weilnetz.de/w64/ (the standard Windows
   build). Needs admin rights once.
2. The UEFI firmware tup needs ships **inside that install**:
   `C:\Program Files\qemu\share\edk2-aarch64-code.fd`.
3. From PowerShell, in the folder holding the image:

```powershell
& "C:\Program Files\qemu\qemu-system-aarch64.exe" `
  -machine virt -cpu cortex-a72 -m 2048 -smp 2 `
  -drive if=pflash,format=raw,readonly=on,file="C:\Program Files\qemu\share\edk2-aarch64-code.fd" `
  -drive file=tup-0.1-arm64.qcow2,format=qcow2,if=virtio `
  -nographic
```

The console runs in that terminal. `tup login:` is the finish line; log in
as `root`. To quit QEMU: `Ctrl-a` then `x`.

## Path B — WSL2 (if the machine has it)

Inside a WSL2 Ubuntu, the machine *is* an Ubuntu host — follow
[`RUN-ON-UBUNTU.md`](RUN-ON-UBUNTU.md) verbatim (`sudo apt-get install
qemu-system-arm qemu-efi-aarch64`, one command, done). Same measured 40 s
class of boot.

## What you are looking at, once it boots

Same checks as everywhere: `cat /etc/os-release` says `NAME="tup"`;
`claude --version` answers from the agent layer; every file on the disk is
accounted for in the repo's `receipts/`.

## Record the witness

Nobody has booted tup on Windows yet. If you do, that is a fact worth
keeping: note the Windows version, QEMU version, and time-to-login, and
drop it in `receipts/` as `boot-witness-windows-<date>.txt` (a photo of the
login prompt is a fine start). The house rule is that claims are measured —
"boots on Windows" becomes true the moment someone writes down that it did.
