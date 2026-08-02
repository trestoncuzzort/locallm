#!/usr/bin/env python3
"""install.py - set this app up on this computer, picking parts to match it.

Run it once. It builds a private Python environment next to this file, installs
PyTorch in the version that suits your graphics card, checks the result, and
puts a "Train My AI" shortcut on your Desktop.

WHY THIS EXISTS. The launchers used to point at a fixed folder that only ever
existed on the machine the app was written on. On anyone else's computer the
window printed "The system cannot find the path specified" and closed -- and
reported SUCCESS while doing it, so nothing downstream could tell. Setting the
app up by hand meant knowing what a virtual environment is, which version of
PyTorch matches your graphics card, and where the wheel index lives. That is
three pieces of knowledge this file now holds instead of the user.

STDLIB ONLY, AND IT MUST STAY THAT WAY. This is the first thing that runs on a
computer where nothing is installed yet. Importing anything third-party here --
including torch -- would make it die with a traceback on exactly the machine it
exists to help. Same discipline as check_my_computer.py, for the same reason.

WHAT IT DOES NOT DO. It does not install Python (it cannot; it IS Python), it
does not touch the registry, it does not need administrator rights, and it
writes nothing outside this folder except one Desktop shortcut. Undoing it is
deleting the .venv folder and that shortcut.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / ".venv"
MIN_PYTHON = (3, 10)

# Matches the build this app is developed and measured against. CUDA 12.1 wheels
# run on any driver new enough for CUDA 12.x, which is why the index is pinned to
# a version rather than to "latest": a newer CUDA line can require a newer driver
# than the user has, and the failure shows up as "torch installed fine but sees
# no graphics card", which is a miserable thing to debug from a distance.
CUDA_INDEX = "https://download.pytorch.org/whl/cu121"
CPU_INDEX = "https://download.pytorch.org/whl/cpu"


def say(msg: str = "") -> None:
    print(msg, flush=True)


def step(n: int, total: int, msg: str) -> None:
    say(f"\n[{n}/{total}] {msg}")


def has_nvidia_gpu() -> tuple[bool, str]:
    """Is there an NVIDIA graphics card this machine can train on?

    Asks nvidia-smi, which ships with the driver. Its ABSENCE is the signal --
    no driver, no CUDA-capable card worth installing CUDA wheels for. This is
    deliberately not a torch call: torch is what we have not installed yet.
    """
    exe = shutil.which("nvidia-smi")
    if not exe:
        return False, "no NVIDIA driver found (nvidia-smi is not on this computer)"
    try:
        p = subprocess.run([exe, "--query-gpu=name,memory.total",
                            "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"nvidia-smi did not answer ({e.__class__.__name__})"
    if p.returncode != 0 or not p.stdout.strip():
        return False, "nvidia-smi reported no graphics card"
    return True, p.stdout.strip().splitlines()[0].strip()


def candidate_pythons() -> list[tuple[tuple[int, int], str]]:
    """Every Python on this computer that could host the app, newest first.

    The one running this script is included, but it is NOT assumed to be the
    right one -- see pick_python(). On Windows the `py` launcher knows where the
    others are; if it is missing we simply have one candidate.
    """
    found: dict[str, tuple[int, int]] = {}
    v = sys.version_info
    found[sys.executable] = (v.major, v.minor)

    exe = shutil.which("py")
    if exe:
        try:
            p = subprocess.run([exe, "-0p"], capture_output=True, text=True,
                               timeout=60)
            for raw in p.stdout.splitlines():
                # Lines look like: " -V:3.12          C:\...\python.exe"
                line = raw.strip()
                if not line.startswith("-V:"):
                    continue
                tag, _, path = line.partition(" ")
                path = path.strip().strip("*").strip()
                ver = tag[3:].split("-")[0]          # "3.12-32" -> "3.12"
                try:
                    major, minor = (int(x) for x in ver.split(".")[:2])
                except ValueError:
                    continue
                if path and Path(path).exists():
                    found[path] = (major, minor)
        except (OSError, subprocess.TimeoutExpired):
            pass

    return sorted(((ver, path) for path, ver in found.items()), reverse=True)


def torch_is_available_for(python_exe: str, index: str) -> bool:
    """Can pip actually find a PyTorch for this interpreter?

    ASKED, NOT ASSUMED, and this is the point of the function. PyTorch ships
    wheels for a moving range of Python versions: at the time of writing there
    is nothing for 3.14, which is precisely what python.org offers as the
    current download. A new user installing Python today, doing everything
    right, lands on the one version that cannot work -- the real message was

        ERROR: Could not find a version that satisfies the requirement torch
               (from versions: none)

    The tempting fix is a hardcoded "3.10 to 3.13" table. That table is wrong
    the moment PyTorch ships 3.14 wheels, and nothing would tell us. So this
    asks the real index instead and lets the answer come from PyTorch.

    `pip index versions` and NOT `pip install --dry-run`. The first version of
    this used --dry-run and it was a mistake worth recording: --dry-run still
    RESOLVES, which for torch means walking the whole CUDA dependency tree and
    pulling wheels to read their metadata. Measured mid-run, the pip cache was
    at 3.0 GB and a single probe had not finished. A yes/no question must not
    cost gigabytes per interpreter. `index versions` fetches the index page and
    filters by this interpreter's own compatibility tags, which is exactly the
    question being asked and nothing more.
    """
    try:
        p = subprocess.run(
            [python_exe, "-m", "pip", "index", "versions", "torch",
             "--index-url", index, "--no-input"],
            capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if p.returncode != 0:
        return False
    # "torch (2.5.1+cu121)" / "Available versions: ..." on success; on a Python
    # with no wheels pip exits non-zero with "no matching distribution".
    return "available versions" in p.stdout.lower() or bool(p.stdout.strip())


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts" if os.name == "nt" else "bin") / (
        "python.exe" if os.name == "nt" else "python")


def run(cmd: list[str], what: str, dry: bool) -> None:
    """Run a step, and FAIL LOUDLY. Every command here is one the user is
    waiting on; a silent failure would leave a half-built environment that
    looks finished."""
    if dry:
        say(f"      would run: {' '.join(str(c) for c in cmd)}")
        return
    p = subprocess.run(cmd)
    if p.returncode != 0:
        raise SystemExit(
            f"\n  SETUP STOPPED: {what} failed (code {p.returncode}).\n"
            f"  Command: {' '.join(str(c) for c in cmd)}\n"
            f"  Nothing outside this folder was changed. Fix the problem above\n"
            f"  and run INSTALL.bat again -- it is safe to re-run.")


def make_desktop_shortcut(dry: bool) -> str:
    """Put 'Train My AI' on the Desktop. Best effort, never fatal.

    A missing shortcut is a convenience the user can live without; the app still
    starts from the folder. So this reports what happened and returns, rather
    than throwing away a successful install over it.
    """
    target = HERE / "Train My AI.bat"
    desktop = Path(os.path.expanduser("~")) / "Desktop"
    if os.name != "nt":
        return "skipped (not Windows)"
    if not desktop.is_dir():
        return "skipped (no Desktop folder found)"
    link = desktop / "Train My AI.lnk"
    if dry:
        return f"would create {link}"
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut("
        f"'{link}');"
        f"$s.TargetPath='{target}';"
        f"$s.WorkingDirectory='{HERE}';"
        "$s.Save()"
    )
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                            "-Command", ps],
                           capture_output=True, text=True, timeout=120)
        if p.returncode == 0 and link.exists():
            return f"created {link}"
        return f"could not create one ({(p.stderr or '').strip()[:80]})"
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"could not create one ({e.__class__.__name__})"


def main() -> int:
    ap = argparse.ArgumentParser(description="Set up Train My AI on this computer.")
    ap.add_argument("--dry-run", action="store_true",
                    help="show every step and change nothing")
    ap.add_argument("--cpu-only", action="store_true",
                    help="install the processor-only build even if a graphics "
                         "card is present")
    args = ap.parse_args()
    dry = args.dry_run
    total = 5

    say("=" * 68)
    say("  TRAIN MY AI - SETUP")
    say("=" * 68)
    if dry:
        say("  DRY RUN. Nothing will be installed or changed.")

    # ---- 1. Python -------------------------------------------------------
    step(1, total, "Checking Python")
    v = sys.version_info
    say(f"      Python {v.major}.{v.minor}.{v.micro} at {sys.executable}")
    if (v.major, v.minor) < MIN_PYTHON:
        say(f"\n  This app needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer.")
        say("  Get it from https://www.python.org/downloads/ and tick")
        say('  "Add python.exe to PATH" during setup, then run this again.')
        return 1

    # ---- 2. Graphics card ------------------------------------------------
    step(2, total, "Looking at your graphics card")
    gpu, detail = has_nvidia_gpu()
    if args.cpu_only:
        gpu = False
        detail = "overridden by --cpu-only"
    say(f"      {detail}")
    index = CPU_INDEX if not gpu else CUDA_INDEX
    if gpu:
        say("      -> installing the graphics-card build (much faster to train)")
    else:
        say("      -> installing the processor-only build")
        say("         Training will still work. It will be slower.")

    # ---- 3. Private environment -----------------------------------------
    step(3, total, f"Building a private Python environment in {VENV.name}")

    # WHICH Python hosts it is not a free choice: PyTorch must have a wheel for
    # that exact version. Ask the index rather than trusting the interpreter
    # that happens to have launched this file -- on this machine that was 3.14,
    # for which PyTorch publishes nothing at all.
    host = sys.executable
    if not dry:
        say("      checking which Python versions PyTorch supports...")
        usable = None
        for (major, minor), path in candidate_pythons():
            if (major, minor) < MIN_PYTHON:
                continue
            ok = torch_is_available_for(path, index)
            say(f"      Python {major}.{minor:<3} {'yes' if ok else 'no '}"
                f"  {path}")
            if ok and usable is None:
                usable = path
        if usable is None:
            say("\n  CANNOT SET UP YET.")
            say("  PyTorch does not publish a version for any Python on this")
            say("  computer. The newest Python it supports is usually one or")
            say("  two behind the newest release.")
            say("")
            say("  Fix: install a slightly older Python from")
            say("    https://www.python.org/downloads/")
            say('  tick "Add python.exe to PATH", then run INSTALL.bat again.')
            say("  This setup will find it and use it automatically -- you can")
            say("  keep the Python you already have.")
            return 1
        host = usable
        say(f"      using {host}")

    if VENV.exists():
        say(f"      {VENV.name} already exists -- reusing it.")
        say("      (Delete that folder and re-run for a clean setup.)")
    else:
        run([host, "-m", "venv", str(VENV)],
            "creating the private environment", dry)
    py = venv_python(VENV)
    if not dry and not py.exists():
        raise SystemExit(f"\n  SETUP STOPPED: expected {py} and it is not there.")

    # ---- 4. PyTorch ------------------------------------------------------
    step(4, total, "Installing PyTorch - this is a large download, please wait")
    say(f"      from {index}")
    run([str(py), "-m", "pip", "install", "--upgrade", "pip"],
        "updating pip", dry)
    run([str(py), "-m", "pip", "install", "torch", "--index-url", index],
        "installing PyTorch", dry)

    # ---- 5. Check it actually worked -------------------------------------
    step(5, total, "Checking the result on this computer")
    if dry:
        say(f"      would run: {py} check_my_computer.py")
    else:
        # check_my_computer.py is the existing install check. Running it HERE
        # means setup is confirmed by the same tool the user runs later, not by
        # a second opinion written for this file -- and it writes
        # bench_device_result.json, without which the studio's size presets
        # refuse to estimate a training time.
        p = subprocess.run([str(py), str(HERE / "check_my_computer.py")])
        if p.returncode != 0:
            say("\n  Setup finished, but the check above found a problem.")
            say("  Read what it said -- it names the thing to fix.")
            return 1

    shortcut = make_desktop_shortcut(dry)
    say(f"\n      Desktop shortcut: {shortcut}")

    say("\n" + "=" * 68)
    say("  READY.")
    say("=" * 68)
    say('  Start the app with "Train My AI" on your Desktop, or by opening')
    say('  "Train My AI.bat" in this folder.')
    say("")
    say("  First time? In the app, press \"Get better text...\" to download")
    say("  something worth training on, then pick a size and press Train.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Stopped. Nothing was left half-installed that re-running "
              "will not fix.")
        raise SystemExit(1)
