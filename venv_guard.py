#!/usr/bin/env python3
"""venv_guard.py — one implementation of "run me under the interpreter I need".

THE CLASS THIS CLOSES. This repo has two interpreters: the system Python (3.14,
too new for the training stack) and .venv-train (3.11, where torch/gguf/
safetensors/pyarrow live). Scripts that need the second are naturally launched
with the first, and the failure lands deep inside a function as a
ModuleNotFoundError, after argparse has accepted every flag and printed nothing.

export_adapter.py solved this, citing sync_public.py's test gate as the same
lesson. screen_tasks.py needed it too and got a COPY (section 65), where I wrote
down that the real close was one shared helper and that a third copy did not
justify refactoring. It bit within the hour: build_ruler.py imported
screen_tasks' copy, whose `me = Path(__file__)` is screen_tasks.py, so it
re-executed the wrong script with build_ruler's arguments.

That is the tell that a duplicated helper is not a style problem. The copy was
correct in its own file and wrong the moment it was reused, because it had a
caller baked into it. So: the caller is now a parameter, and there is one copy.

Usage, at the entry point and not at import time:

    if __name__ == "__main__":
        venv_guard.ensure(__file__, "pyarrow")
        main()
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV_PY = HERE / ".venv-train" / "Scripts" / "python.exe"


def ensure(caller: str | Path, *modules: str, install_hint: str = "") -> None:
    """Re-exec `caller` under .venv-train if any of `modules` is missing.

    `caller` must be the calling script's __file__. It is a parameter precisely
    because baking it in is what broke the copied version: a guard that knows
    only its own filename cannot be imported by anyone else.

    No-ops when the modules are already importable, so running under the venv
    directly costs nothing. Uses find_spec rather than importing, so a heavy
    dependency is not loaded just to prove it exists.
    """
    if all(importlib.util.find_spec(m) is not None for m in modules):
        return

    me = Path(caller).resolve()
    if VENV_PY.exists() and Path(sys.executable).resolve() != VENV_PY.resolve():
        r = subprocess.run([str(VENV_PY), str(me), *sys.argv[1:]])
        sys.exit(r.returncode)

    missing = [m for m in modules if importlib.util.find_spec(m) is None]
    raise SystemExit(
        f"{me.name} needs {', '.join(missing)}.\n"
        f"  expected interpreter: {VENV_PY}\n"
        + (f"  {install_hint}\n" if install_hint else
           f"  install into that venv:  .venv-train\\Scripts\\python -m pip "
           f"install {' '.join(missing)}"))
