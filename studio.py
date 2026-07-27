"""studio.py — a GUI for building and training your OWN GPT, from random init.

    python studio.py

No pretrained weights, no API, no downloads. The architecture is assembled from
model.py, the tokenizer is built from your corpus by data.py, and the training loop
is train.py's. This file adds a control surface: knobs, a live loss curve, and a
sampler — it does not reimplement any of the math.

Dependencies: torch + tkinter (stdlib). Nothing else.
"""
from __future__ import annotations

import json
import queue
import sys
import threading
import time
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import torch  # noqa: E402

import runlog  # noqa: E402

from model import GPT, GPTConfig  # noqa: E402
from data import (CharTokenizer, Corpus, documents, group_split,  # noqa: E402
                  split_health)
from leakage import scan as leakage_scan  # noqa: E402
from train import (auto_lr, cosine_lr, enable_fast_math,  # noqa: E402
                   estimate_loss, make_optimizer)


# --------------------------------------------------------------------------
# parameter count, computed analytically so the UI can update it on every
# keystroke without allocating a model. Mirrors GPT.num_params(), which
# excludes the positional embedding table.
# --------------------------------------------------------------------------
def param_count(vocab: int, block: int, n_layer: int, n_head: int,
                n_embd: int, bias: bool = True) -> int:
    b = 1 if bias else 0
    per_block = (
        (3 * n_embd * n_embd + 3 * n_embd * b)      # attn.c_attn
        + (n_embd * n_embd + n_embd * b)            # attn.c_proj
        + (4 * n_embd * n_embd + 4 * n_embd * b)    # mlp.c_fc
        + (4 * n_embd * n_embd + n_embd * b)        # mlp.c_proj
        + 4 * n_embd                                # ln_1 + ln_2 (weight+bias)
    )
    total = (
        vocab * n_embd          # wte (tied to lm_head, counted once)
        + block * n_embd        # wpe
        + n_layer * per_block
        + 2 * n_embd            # ln_f
    )
    return total - block * n_embd


class Fields:
    """Thin wrapper so a labelled row of entries reads as a dict of values."""

    def __init__(self):
        self.vars: dict[str, tk.Variable] = {}

    def add(self, parent, row, label, var, width=10, hint=""):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        e = ttk.Entry(parent, textvariable=var, width=width)
        e.grid(row=row, column=1, sticky="w", pady=2)
        if hint:
            ttk.Label(parent, text=hint, foreground="#888").grid(
                row=row, column=2, sticky="w", padx=6)
        return e


class LossPlot(tk.Canvas):
    """Loss curve drawn by hand — no matplotlib, no extra dependency."""

    BG = "#14161a"
    GRID = "#2a2f38"
    TRAIN = "#4da3ff"
    VAL = "#ff9f43"

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=self.BG, highlightthickness=0, **kw)
        self.train_pts: list[tuple[int, float]] = []
        self.val_pts: list[tuple[int, float]] = []
        self.total_steps = 1
        self.bind("<Configure>", lambda e: self.redraw())

    def reset(self, total_steps: int):
        self.train_pts.clear()
        self.val_pts.clear()
        self.total_steps = max(1, total_steps)
        self.redraw()

    def add(self, step: int, train: float, val: float):
        self.train_pts.append((step, train))
        self.val_pts.append((step, val))
        self.redraw()

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 60 or h < 40:
            return
        pad_l, pad_r, pad_t, pad_b = 52, 12, 14, 26
        x0, y0, x1, y1 = pad_l, pad_t, w - pad_r, h - pad_b

        vals = [v for _, v in self.train_pts] + [v for _, v in self.val_pts]
        lo, hi = (min(vals), max(vals)) if vals else (0.0, 1.0)
        if hi - lo < 1e-6:
            lo, hi = lo - 0.5, hi + 0.5
        pad = (hi - lo) * 0.08
        lo, hi = lo - pad, hi + pad

        for i in range(5):  # horizontal grid + y labels
            y = y0 + (y1 - y0) * i / 4
            self.create_line(x0, y, x1, y, fill=self.GRID)
            self.create_text(x0 - 6, y, anchor="e", fill="#8a91a0",
                             font=("Consolas", 8), text=f"{hi - (hi - lo) * i / 4:.2f}")
        self.create_text((x0 + x1) / 2, h - 8, fill="#8a91a0",
                         font=("Consolas", 8), text=f"step (0 – {self.total_steps})")

        def to_xy(step, val):
            fx = x0 + (x1 - x0) * (step / self.total_steps)
            fy = y1 - (y1 - y0) * ((val - lo) / (hi - lo))
            return fx, fy

        for pts, color in ((self.train_pts, self.TRAIN), (self.val_pts, self.VAL)):
            if len(pts) >= 2:
                flat = []
                for s, v in pts:
                    flat.extend(to_xy(s, v))
                self.create_line(*flat, fill=color, width=2, smooth=True)
            elif len(pts) == 1:
                x, y = to_xy(*pts[0])
                self.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color, outline=color)

        self.create_text(x1 - 4, y0 + 2, anchor="ne", fill=self.TRAIN,
                         font=("Consolas", 9), text="train")
        self.create_text(x1 - 4, y0 + 16, anchor="ne", fill=self.VAL,
                         font=("Consolas", 9), text=getattr(self, "val_label", "val"))


class TrainWorker(threading.Thread):
    """Runs the training loop off the UI thread and reports through a queue."""

    def __init__(self, cfgs: dict, q: queue.Queue, stop: threading.Event):
        super().__init__(daemon=True)
        self.c = cfgs
        self.q = q
        self.stop = stop

    def log(self, msg):
        self.q.put(("log", msg))

    def run(self):
        try:
            self._run()
        except Exception:
            self.q.put(("error", traceback.format_exc()))

    def _run(self):
        c = self.c
        device = c["device"]
        torch.manual_seed(c["seed"])

        text = Path(c["data"]).read_text(encoding="utf-8", errors="ignore")
        tok = CharTokenizer.from_text(text)
        corpus = Corpus(text, tok, device)
        self.log(f"corpus: {len(text):,} chars | vocab {tok.vocab_size} | device {device}")

        # Before reporting a single val number, find out whether it means
        # anything. Validation text that also appears in training measures
        # memorisation, not generalisation.
        tr_txt, va_txt = group_split(text)
        rep = leakage_scan(tr_txt, va_txt)
        health = split_health(text)
        self.val_ok = rep.trustworthy and health["ok"]
        self.log(f"leakage scan: {rep.summary()}")
        if not rep.trustworthy:
            self.log("  !! val loss below is NOT a measure of generalisation. "
                     "Judge this run on TRAIN loss.")
        elif not health["ok"]:
            self.log(f"  !! asked for a 10% val split, got "
                     f"{health['achieved_val_frac']:.1%} (only {health['documents']} "
                     f"documents, largest is {health['largest_doc_frac']:.0%} of the "
                     f"corpus). Val loss is thin. Prefer TRAIN loss.")
        self.q.put(("valtrust", self.val_ok))

        if len(corpus.train) <= c["block_size"]:
            raise ValueError(
                f"corpus too small: train split is {len(corpus.train)} tokens but "
                f"block_size is {c['block_size']}. Use a bigger corpus or a smaller "
                f"context window.")

        cfg = GPTConfig(vocab_size=tok.vocab_size, block_size=c["block_size"],
                        n_layer=c["n_layer"], n_head=c["n_head"],
                        n_embd=c["n_embd"], dropout=c["dropout"])
        model = GPT(cfg).to(device)
        self.log(f"model: {model.num_params() / 1e6:.2f}M params | "
                 f"{c['n_layer']}L {c['n_head']}H {c['n_embd']}D | from random init")

        enable_fast_math()
        opt = make_optimizer(model, c["lr"])
        use_bf16 = device == "cuda" and torch.cuda.is_bf16_supported()
        if use_bf16:
            self.log("autocast: bfloat16")

        steps = c["steps"]
        warmup = max(10, steps // 20)
        t0 = time.time()
        tokens_per_step = c["batch_size"] * c["block_size"]

        for step in range(steps):
            if self.stop.is_set():
                self.log(f"\nSTOPPED by user at step {step}.")
                break

            lr = cosine_lr(step, warmup, steps, c["lr"], c["lr"] / 10)
            for g in opt.param_groups:
                g["lr"] = lr

            if step % c["eval_interval"] == 0 or step == steps - 1:
                L = estimate_loss(model, corpus, c["batch_size"], c["block_size"])
                el = time.time() - t0
                self.q.put(("metrics", {"step": step, "train": L["train"], "val": L["val"],
                                        "lr": lr, "elapsed": el,
                                        "tok_s": tokens_per_step * (step + 1) / max(el, 1e-9)}))
                self.log(f"step {step:5d} | train {L['train']:.4f} | val {L['val']:.4f} "
                         f"| lr {lr:.2e} | {el:.0f}s")

            x, y = corpus.get_batch("train", c["batch_size"], c["block_size"])
            if use_bf16:
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    _, loss = model(x, y)
            else:
                _, loss = model(x, y)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()

        out = Path(c["out"])
        out.mkdir(parents=True, exist_ok=True)
        torch.save({"model": model.state_dict(), "config": cfg.__dict__}, out / "ckpt.pt")
        tok.save(out / "tokenizer.json")
        self.log(f"saved model + tokenizer to {out}/  "
                 f"(generate.py --out {out.name} works on this)")

        # Every GUI run lands in the same append-only log as every CLI run, so a
        # week of experimenting leaves a reviewable trail instead of a folder of
        # checkpoints nobody can tell apart.
        wall = time.time() - t0
        final = estimate_loss(model, corpus, c["batch_size"], c["block_size"])
        runlog.record("train", device=device, out=str(out), source="studio",
                      corpus=runlog.corpus_fingerprint(text),
                      config={k: c[k] for k in ("n_layer", "n_head", "n_embd",
                                                "block_size", "batch_size",
                                                "steps", "lr", "dropout", "seed")},
                      metrics={"train_loss": final["train"], "val_loss": final["val"],
                               "wall_s": wall,
                               "ms_per_step": wall / max(c["steps"], 1) * 1000,
                               "params": model.num_params()},
                      leakage={"verdict": rep.verdict,
                               "content_frac": rep.shingle_frac})
        self.log(f"recorded to {runlog.LOG.name} "
                 f"(run `python runlog.py` to see every run so far)")
        self.q.put(("done", {"model": model, "tok": tok, "device": device,
                             "elapsed": time.time() - t0}))


class Studio(ttk.Frame):
    def __init__(self, root):
        super().__init__(root, padding=8)
        self.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.q: queue.Queue = queue.Queue()
        self.stop_evt = threading.Event()
        self.worker: TrainWorker | None = None
        self.model = None
        self.tok = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.vocab = 0

        self._build_left()
        self._build_right()
        self._scan_corpus(quiet=True)
        self._update_params()
        self.after(100, self._drain)

    # ---------------------------------------------------------------- left
    def _build_left(self):
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 8))

        # --- corpus
        box = ttk.LabelFrame(left, text="1 · CORPUS  (your text = your vocabulary)")
        box.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.v_data = tk.StringVar(value=str(HERE / "corpus.txt"))
        ttk.Entry(box, textvariable=self.v_data, width=34).grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(6, 2))
        ttk.Button(box, text="Browse…", command=self._browse).grid(
            row=1, column=0, sticky="w", padx=8, pady=(0, 6))
        ttk.Button(box, text="Scan", command=self._scan_corpus).grid(
            row=1, column=1, sticky="w", pady=(0, 6))
        self.l_corpus = ttk.Label(box, text="—", foreground="#555")
        self.l_corpus.grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 6))

        # --- architecture
        arch = ttk.LabelFrame(left, text="2 · ARCHITECTURE  (built from random init)")
        arch.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        f = Fields()
        self.v_layer = tk.StringVar(value="4")
        self.v_head = tk.StringVar(value="4")
        self.v_embd = tk.StringVar(value="256")
        self.v_block = tk.StringVar(value="128")
        self.v_drop = tk.StringVar(value="0.1")
        f.add(arch, 0, "layers", self.v_layer, hint="depth")
        f.add(arch, 1, "heads", self.v_head, hint="n_embd must divide by this")
        f.add(arch, 2, "embed dim", self.v_embd, hint="width")
        f.add(arch, 3, "context", self.v_block, hint="block_size")
        f.add(arch, 4, "dropout", self.v_drop)
        for v in (self.v_layer, self.v_head, self.v_embd, self.v_block):
            v.trace_add("write", lambda *_: self._update_params())
        self.l_params = ttk.Label(arch, text="", font=("Consolas", 10, "bold"))
        self.l_params.grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 6))

        # --- training
        tr = ttk.LabelFrame(left, text="3 · TRAINING")
        tr.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.v_steps = tk.StringVar(value="2000")
        self.v_batch = tk.StringVar(value="32")
        self.v_lr = tk.StringVar(value=f"{auto_lr(256):.2g}")
        self._auto_lr_shown = self.v_lr.get()  # so a user override is never clobbered
        self.v_eval = tk.StringVar(value="100")
        self.v_seed = tk.StringVar(value="1337")
        self.v_out = tk.StringVar(value="out_gui")
        f.add(tr, 0, "steps", self.v_steps)
        f.add(tr, 1, "batch size", self.v_batch)
        f.add(tr, 2, "learn rate", self.v_lr, hint="auto: scales with width")
        f.add(tr, 3, "eval every", self.v_eval, hint="steps")
        f.add(tr, 4, "seed", self.v_seed)
        f.add(tr, 5, "save to", self.v_out, width=16)
        self.v_cpu = tk.BooleanVar(value=False)
        ttk.Checkbutton(tr, text="force CPU", variable=self.v_cpu).grid(
            row=6, column=0, columnspan=2, sticky="w", padx=8, pady=(2, 6))

        # --- run
        run = ttk.Frame(left)
        run.grid(row=3, column=0, sticky="ew")
        self.b_train = ttk.Button(run, text="▶  Train from scratch", command=self._start)
        self.b_train.grid(row=0, column=0, sticky="ew", ipady=4)
        self.b_stop = ttk.Button(run, text="■  Stop", command=self._stop, state="disabled")
        self.b_stop.grid(row=0, column=1, padx=(6, 0), ipady=4)
        run.columnconfigure(0, weight=1)

    # --------------------------------------------------------------- right
    def _build_right(self):
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=3)
        right.rowconfigure(1, weight=2)

        self.plot = LossPlot(right, height=240)
        self.plot.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        logbox = ttk.LabelFrame(right, text="LOG")
        logbox.grid(row=1, column=0, sticky="nsew")
        logbox.columnconfigure(0, weight=1)
        logbox.rowconfigure(0, weight=1)
        self.log = tk.Text(logbox, height=10, bg="#14161a", fg="#c8d0dc",
                           insertbackground="#c8d0dc", font=("Consolas", 9),
                           wrap="word", relief="flat")
        self.log.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        sb = ttk.Scrollbar(logbox, command=self.log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.log["yscrollcommand"] = sb.set

        gen = ttk.LabelFrame(right, text="4 · GENERATE  (from the model you just trained)")
        gen.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        gen.columnconfigure(1, weight=1)
        self.v_prompt = tk.StringVar(value="def ")
        self.v_tokens = tk.StringVar(value="400")
        self.v_temp = tk.StringVar(value="0.8")
        self.v_topk = tk.StringVar(value="40")
        ttk.Label(gen, text="prompt").grid(row=0, column=0, padx=(8, 4), pady=4, sticky="w")
        ttk.Entry(gen, textvariable=self.v_prompt).grid(row=0, column=1, sticky="ew", pady=4)
        knobs = ttk.Frame(gen)
        knobs.grid(row=1, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 6))
        for i, (lbl, var) in enumerate((("tokens", self.v_tokens),
                                        ("temp", self.v_temp),
                                        ("top-k", self.v_topk))):
            ttk.Label(knobs, text=lbl).grid(row=0, column=i * 2, padx=(0 if i == 0 else 10, 4))
            ttk.Entry(knobs, textvariable=var, width=7).grid(row=0, column=i * 2 + 1)
        self.b_gen = ttk.Button(gen, text="Sample", command=self._generate, state="disabled")
        self.b_gen.grid(row=0, column=2, padx=6)

        self.status = ttk.Label(self, text="", foreground="#555")
        self.status.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self._set_status(f"idle · device {self.device}")

    # ------------------------------------------------------------- helpers
    def _set_status(self, msg):
        self.status.config(text=msg)

    def _write(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def _browse(self):
        p = filedialog.askopenfilename(title="Pick a .txt corpus",
                                       filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if p:
            self.v_data.set(p)
            self._scan_corpus()

    def _scan_corpus(self, quiet=False):
        p = Path(self.v_data.get())
        if not p.is_file():
            self.l_corpus.config(text="file not found", foreground="#c0392b")
            self.vocab = 0
            self._update_params()
            return
        text = p.read_text(encoding="utf-8", errors="ignore")
        self.vocab = len(set(text))
        try:
            tr_txt, va_txt = group_split(text)
            rep = leakage_scan(tr_txt, va_txt)
            health = split_health(text)
            colour = {"CLEAN": "#2d7d46", "SUSPECT": "#b8860b",
                      "CONTAMINATED": "#c0392b"}[rep.verdict]
            note = rep.verdict
            if rep.trustworthy and not health["ok"]:
                colour, note = "#b8860b", f"thin val ({health['achieved_val_frac']:.0%})"
        except Exception:                       # never let the scan block training
            colour, note, rep = "#2d7d46", "unscanned", None
        self.l_corpus.config(
            text=f"{len(text):,} chars · vocab {self.vocab} · "
                 f"{len(documents(text)):,} docs · leakage: {note}",
            foreground=colour)
        self._update_params()
        if not quiet:
            self._write(f"scanned {p.name}: {len(text):,} chars, vocab {self.vocab}")
            if rep is not None:
                self._write(rep.report())

    def _ints(self):
        return (int(self.v_layer.get()), int(self.v_head.get()),
                int(self.v_embd.get()), int(self.v_block.get()))

    def _update_params(self):
        try:
            n_layer, n_head, n_embd, block = self._ints()
            if n_embd % n_head != 0:
                self.l_params.config(
                    text=f"✗  embed dim {n_embd} not divisible by {n_head} heads",
                    foreground="#c0392b")
                return
            n = param_count(max(self.vocab, 1), block, n_layer, n_head, n_embd)
            self.l_params.config(text=f"≈ {n / 1e6:.2f}M parameters  "
                                      f"({n:,} weights, yours)", foreground="#2d7d46")
            # Track the width: 3e-4 is a GPT-2-scale constant and is wrong here.
            # Only retarget the LR if the user has not typed their own value.
            if getattr(self, "_auto_lr_shown", None) == self.v_lr.get():
                new = f"{auto_lr(n_embd):.2g}"
                self.v_lr.set(new)
                self._auto_lr_shown = new
        except (ValueError, ZeroDivisionError):
            self.l_params.config(text="…", foreground="#888")

    # ---------------------------------------------------------------- run
    def _start(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            n_layer, n_head, n_embd, block = self._ints()
            cfg = {
                "data": self.v_data.get(),
                "out": self.v_out.get(),
                "n_layer": n_layer, "n_head": n_head, "n_embd": n_embd,
                "block_size": block, "dropout": float(self.v_drop.get()),
                "steps": int(self.v_steps.get()), "batch_size": int(self.v_batch.get()),
                "lr": float(self.v_lr.get()), "eval_interval": int(self.v_eval.get()),
                "seed": int(self.v_seed.get()),
                "device": "cpu" if self.v_cpu.get() else self.device,
            }
        except ValueError as e:
            messagebox.showerror("Bad setting", f"Could not read a number: {e}")
            return
        if n_embd % n_head != 0:
            messagebox.showerror("Bad architecture",
                                 f"embed dim {n_embd} must be divisible by {n_head} heads.")
            return
        if not Path(cfg["data"]).is_file():
            messagebox.showerror("No corpus", f"Not a file:\n{cfg['data']}")
            return

        self.log.delete("1.0", "end")
        self.plot.reset(cfg["steps"])
        self.stop_evt.clear()
        self.b_train.config(state="disabled")
        self.b_stop.config(state="normal")
        self.b_gen.config(state="disabled")
        self._write(f"=== training from random init · {time.strftime('%H:%M:%S')} ===")
        self.worker = TrainWorker(cfg, self.q, self.stop_evt)
        self.worker.start()

    def _stop(self):
        self.stop_evt.set()
        self.b_stop.config(state="disabled")
        self._set_status("stopping after this step…")

    def _generate(self):
        if self.model is None:
            return
        try:
            tokens = int(self.v_tokens.get())
            temp = float(self.v_temp.get())
            topk = int(self.v_topk.get())
        except ValueError as e:
            messagebox.showerror("Bad setting", str(e))
            return

        self.b_gen.config(state="disabled")
        self._set_status("sampling…")

        def work():
            try:
                ids = self.tok.encode(self.v_prompt.get()) or [0]
                idx = torch.tensor([ids], dtype=torch.long, device=self.device)
                self.model.eval()
                out = self.model.generate(idx, tokens, temperature=temp, top_k=topk)
                self.q.put(("sample", self.tok.decode(out[0].tolist())))
            except Exception:
                self.q.put(("error", traceback.format_exc()))

        threading.Thread(target=work, daemon=True).start()

    # -------------------------------------------------------------- pump
    def _drain(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    self._write(payload)
                elif kind == "valtrust":
                    self.val_ok = payload
                    self.plot.val_label = "val" if payload else "val (untrusted)"
                elif kind == "metrics":
                    m = payload
                    self.plot.add(m["step"], m["train"], m["val"])
                    vtag = "val" if getattr(self, "val_ok", True) else "val*"
                    self._set_status(
                        f"step {m['step']} · train {m['train']:.4f} · {vtag} {m['val']:.4f} "
                        f"· {m['elapsed']:.0f}s · {m['tok_s']:,.0f} tok/s"
                        + ("" if getattr(self, "val_ok", True)
                           else "   (* leakage detected, judge on train)"))
                elif kind == "done":
                    self.model = payload["model"]
                    self.tok = payload["tok"]
                    self.device = payload["device"]
                    self.b_train.config(state="normal")
                    self.b_stop.config(state="disabled")
                    self.b_gen.config(state="normal")
                    self._set_status(f"done in {payload['elapsed']:.0f}s · "
                                     f"model live — press Sample")
                elif kind == "sample":
                    self._write("\n--- sample from YOUR model ---\n" + payload + "\n")
                    self.b_gen.config(state="normal")
                    self._set_status("idle")
                elif kind == "error":
                    self._write("\n!!! ERROR\n" + payload)
                    self.b_train.config(state="normal")
                    self.b_stop.config(state="disabled")
                    if self.model is not None:
                        self.b_gen.config(state="normal")
                    self._set_status("error — see log")
        except queue.Empty:
            pass
        self.after(100, self._drain)


def main():
    root = tk.Tk()
    root.title("localllm studio — build & train your own GPT from scratch")
    root.geometry("1120x760")
    root.minsize(900, 620)
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    Studio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
