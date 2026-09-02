# Run t on a Windows PC

t itself is plain Python 3.12 with no dependencies; the kernels do the
proving. Five of the seven have real Windows builds, verified against their
release listings on 2026-09-02 (the asset names below are copied from those
listings, not guessed). Nobody here has run t on an actual Windows machine
yet, so every behavioural claim on this page is UNVERIFIED until someone
does, and the last section says what to record when you do.

The honest summary first: **WSL2 gives you all seven kernels** by following
the Ubuntu instructions verbatim inside an Ubuntu WSL2 distribution.
**Native Windows gives you five**, which is plenty: `run_all.py` refuses to
conclude from fewer than two kernels, records every absent one with the
exact places it looked, and treats a partial matrix as a smaller real
measurement, not a failure. Five kernels agreeing and refuting is
legitimate cross-kernel verification.

## The five native kernels, with their verified release assets

| Kernel | Asset (from the release page) | Where |
|---|---|---|
| Dafny 4.11.0 | `dafny-4.11.0-x64-windows-2022.zip` | github.com/dafny-lang/dafny, tag v4.11.0 |
| Verus 0.2026.08.30 | `verus-0.2026.08.30.b432e82-x86-win.zip` | github.com/verus-lang/verus (needs rustup: rustup.rs ships rustup-init.exe) |
| F* 2026.08.30 | `fstar-v2026.08.30-Windows_NT-x86_64.zip` | github.com/FStarLang/FStar, tag v2026.08.30 |
| GNATprove FSF 16.1.0 | `gnatprove-x86_64-windows64-16.1.0-1.tar.gz` | github.com/alire-project/GNAT-FSF-builds, tag gnatprove-16.1.0-1 |
| Lean 4.33.1 | `elan-x86_64-pc-windows-msvc.zip`, then `elan default leanprover/lean4:v4.33.1` | github.com/leanprover/elan |

The two that stay on WSL2: **Rocq** and **Frama-C** install through opam,
which is Unix-oriented. Rocq has a native Windows route via the Coq
Platform installer plus `T_COQC` pointing at its `coqc.exe`, but that is
untried here; Frama-C's own documentation points Windows users at WSL2.

## Pointing t at the binaries

Discovery tries, in order: a `T_*` environment variable, then `PATH`, then
glob patterns under your home directory (`.exe` variants are tried
automatically). On Windows the reliable route is the environment variable.
The names, from `verifiers/discover.py`: `T_DAFNY`, `T_VERUS_BIN`,
`T_GNATPROVE`, `T_FRAMAC`, `T_LEAN_BIN`, `T_COQC`, `T_FSTAR`.

PowerShell example:

```powershell
$env:T_DAFNY   = "C:\tools\dafny\dafny.exe"
$env:T_FSTAR   = "C:\tools\fstar\bin\fstar.exe"
cd path\to\tup\t
python run_all.py        # or: py -3 run_all.py
```

`run_all.py` prints one line per absent kernel saying exactly where it
looked. Two or more present kernels and the suite runs; fewer and it
refuses, by design, because agreement measured on nothing is one opinion,
or none.

## What was made portable, and how it was tested without a Windows box

The parallel drivers used to hard-select the `fork` start method, which
does not exist on Windows; they now select fork where it exists and spawn
elsewhere (`verifiers.mp_context`). The live-run guard used to scan
`/proc`, which also does not exist on Windows; a lock file in `out/` now
provides mutual exclusion on every platform, with the Linux `/proc` scan
kept as an extra check where it works. The spawn branch was exercised on
Linux by forcing it (`T_MP_START=spawn`) through the full 77-cell matrix.
The Windows-specific liveness check inside the lock is UNVERIFIED and
fails closed: a stale lock refuses with the file's path so you can delete
it by hand.

## Record the witness

Nobody has run t on Windows yet. If you do, that fact is worth keeping:
note the Windows version, which kernels you installed and from which
assets, what `run_all.py` printed for present and absent kernels, and the
final agreement line. Drop it in `t/` as
`WITNESS-windows-<date>.md`. Claims here become true the moment someone
writes down that they happened.
