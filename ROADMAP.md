# srlm-forge: One Program, Two Instruments — Research Roadmap

**Repo:** this repository, everything on `main` · **Paper:** manuscript v15 (LaTeX tree kept outside the repo; Markdown chain at `docs/revision-2026-08-25/`) · **Hardware:** MacBook M5 Pro (MPS, no CUDA), ubuntu-box (GPU 0 only), the retired Windows 4080/t box (artifact recovery only)

---

## 1. The unifying thesis

The two tracks and the paper are not a training project plus a toy plus a write-up. They are **one research program in measurement-integrity engineering for empirical ML**, whose central claim the paper already states: *an execution-grounded verdict is objective but not thereby trustworthy — instruments do not announce when they stop measuring, so the verdict channel must be treated as adversarial and every benchmark gain decomposed against the instrument's idiosyncrasies before attribution.*

The program has three components with distinct roles:

- **Track A (repo root)** is the *field site*: an 8B DPO pipeline whose real product is the catalogue of eight ways its own instruments kept emitting well-formed numbers after they stopped measuring, plus the gates built in response (hash-receipt dataset gate, pinned verifier, frozen ruler, preregistration, drift guard).
- **Track B (`locallm/`)** is the *controlled laboratory*: a from-scratch 3M–19M char-GPT where every mechanism the 8B pipeline can only observe twice (massive-activation optimizer corruption, seed-vs-function decoupling, disattenuation estimator behavior) can be swept parametrically in minutes on MPS, under the same preregistration discipline.
- **The paper** is the first report from the field site. Its most transferable contribution is the method, and the method is currently *described*, not *shipped*.

The unification move, therefore, is not "merge two codebases." It is: **extract the shared epistemic core (receipts, ledgers, claim-binding, prereg schema, red-witness discipline) into one runnable artifact, prove transfer by cross-gating each track with the other's missing instrument, and use each track to discharge the other's — and the paper's — named limitations.** Every surviving proposal is an instance of that move.

---

## 2. NOW — MacBook, this week, no GPU box

Ordered by evidence-per-effort. All CPU/MPS; nothing touches the Dell except two clearly-marked optional probes.

### WS-1: Statistics core + in-system seed variance *(hours; salvaged from the killed proposal)*

- Extract Welch/incomplete-beta-t from `analyze_run1.py` into `stats_core.py`; **add TOST** (it exists nowhere in the repo — the paper's TOST arithmetic was hand-derived) built on the same `t_sf`.
- Self-test against retained raw rows: `analyze_run1.py` already reproduces Table 1 exactly on this Mac (t=0.656, df=74.0, p=.5140); assert the published TOST values (.0024 / .0433 / .295) too.
- Run a synthetic-Gaussian Monte Carlo coverage certificate of both procedures (CPU minutes).
- Decompose seed-vs-replicate variance from the **existing** `hc-seed01..25` rows in `data/ruler_noise.jsonl` (11 seeds × 40 replicates, real instrument): between-seed SD of arm means 0.0054 vs within-seed 0.0319 → σ_seed ≈ 0.002. Run the 55 true-null seed-pair Welch comparisons for an in-system empirical FPR. This is the deliverable `OPEN-ITEMS.md:26-35` asks for, at zero GPU-hours, and it sizes Run 2.

### WS-2: Contamination transplant *(1–2 days; merges the two leakage survivors)*

Two scans, both verified runnable today from local files, both banked as witnesses in `docs/port-2026-08-24/` style:

- **Scan A — corpus vs ruler:** all 918 chosen/rejected halves of `data/dpo_pairs_capped.jsonl` (plus the 1,244-pair parent and `repair_pairs.jsonl`) against the 31 ruler payloads, loaded from `data/screen_results.jsonl` and re-verified against `ruler_frozen.json`'s `task_sha256` (**not** via `verify_frozen()`, which returns hashes only). Already smoke-run: 31/31 CLEAN, 0.0% overlap, 9.5–10.8 s CPU. The v16 sentence is bounded: "no verbatim or ≥74-char content overlap; paraphrase-level duplication out of scope (scanner's measured 0% rename recall)." Anchor to `body-1.tex:59` / `body-4.tex:15`, **not** Limitation 4. Important honesty note: the 918 pairs come from the 13 seed tasks, zero AceCode rows — this scan bounds one contamination mode, it does not settle AceCode-internal near-duplication.
- **Scan B — training pool vs ruler:** the 43-tid pool payloads vs the 31 ruler payloads. This is the scan that mechanizes `prereg_track_a_run1.json:91`'s disjointness claim *before* run 1 ever generates a corpus from that pool, and it is what the future gate field should carry — **per-task max shingle fraction, never the corpus-aggregate verdict** (one fully-leaked task ≈ 3% of shingles and would read CLEAN under the 20% threshold).
- **Direction 2 — gate Track B:** `train.py` already computes the leakage verdict inline; the real gap is refusal. Add refuse-on-CONTAMINATED and refuse-on-`verify_claims.py`-failure (computed at train time, sub-second), refusal reason appended to `runs.jsonl`. Do not refuse on a merely-absent verdict file — that breaks the beginner double-click flow.
- The canonicalized-identifier second pass (via `measure_bank_concentration`'s `_Canon` + `ast.unparse`, ~10 lines) ships as *diagnostic only* until it has a measured false-positive floor.
- Gate/schema integration into `dataset_gate.py` is **staged behind WS-4's dialect decision** — no receipt schema bump yet.

### WS-3: `verify_paper.py` — manuscript claim binding *(2–3 days)*

The Track B `verify_claims.py` pattern aimed at `/home/me/Documents/research/v15-arxiv/tex/`:

- `paper_claims.json` manifest: Table 1 → `analyze_run1.py` recomputation; MDE/N → `prereg_track_a_run1.json`; dataset facts → `dataset_gate.load_verified()`; concentration → `bank_concentration.json`; mutant survival → `test_adequacy.json`; ruler sha → `ruler_frozen.json`. Note t/p/CI live in `body-2.tex:28` and Appendix A, not in `tables.tex:26-27`.
- **Corrected expectations:** both Table 1 arms now verify from retained bytes (the 40 null replicates were merged back at commit `eb6ff4b`), so the checker's *first genuine catch is the paper's own stale 5-of-40 retention disclosure* (Appendix C, Table 1 note, F3) — a live, publishable erratum on day one, and better evidence for the thesis than the originally-planned "archival" demo.
- Hash rule: content→CRLF canonical for the paper's printed digests (`85fc0bdc…`, `15770d4d…`), with raw digest + platform recorded alongside — otherwise every hash check false-fails against the LF checkout.
- Recall calibration against the 2026-08-22 dossier: denominator = the **29 CONFIRMED** discrepancies annotated in/out-of-scope for digit-binding (not all 42; 5 are refuted, 3 pending, several are wording disputes). The v3–v9 drafts are Markdown, so budget the second extraction frontend as real work, not incidental.
- Pin the artifact state the manifest binds (named commit) and say so in the census appendix. Output classes: machine-verified / archival / withdrawn — with the archival class honestly smaller than first advertised.

### WS-4: Provenance core — `methodkit` *(3–5 days; merges "methodkit" + "Three-OS Verdict Invariance")*

The single most consequential design decision, written against the **post-`c4290b4` world** (the live receipt is schema 5, LF-dialect, `python 3.12.10`, and the gate already passes on this Mac via `SRLM_VERIFY_PY` — the old "Mac fails closed / CRLF fixed point" framing is stale, including the memory note that encodes it):

- **Declared-dialect receipts:** the canonical dialect is a schema-versioned *field of each receipt*, not a fixed CRLF constant. `methodkit` hashes `canonical(blob, receipt.dialect)`. The live LF receipt verifies unchanged with zero regeneration; the paper's printed CRLF digests survive as checkable historical values. Flagship test, parameterized both ways on one committed blob: `dpo_pairs_capped.jsonl` → `0bb9a659…` under `dialect=lf` (live receipt) and `85fc0bdc…` under `dialect=crlf` (paper). This is Failure 8's prescribed repair, landed — and it is *more* urgent than originally pitched, because the paper's printed digest currently dangles against the live receipt (exactly the "reads like tampering" failure the program documents), and default-config Windows clones now fail against the LF receipt: the dialect problem flipped platforms, it did not go away.
- **Placement:** `methodkit` lives **inside `locallm/`** (the public MIT repo ships the citable artifact; Track A imports from the subtree — private-depends-on-public, one copy of each file per commit `8b2ed44`). It must read schema-5 receipts backward-compatibly; no `SCHEMA` bump, no regeneration — that decision stays the maintainer-gated per `docs/UBUNTU-BOOTSTRAP.md`.
- **Platform-aware `verify_py`:** replace the hardcode at `dataset_gate.py:116` and the five remaining duplicates (`poscontrol/run_interleaved.py:34` is already platform-aware), keeping `SRLM_VERIFY_PY` and fail-loud. Rewrite `tests/test_verifier_pin.py`'s Windows-venv precondition POSIX-aware rather than deleting it. This is hygiene now, not a blocker — the Dell has been running around it since 08-25 — but it is ~an hour and removes a standing trap. Use `dataset_gate.require_verified` for the green proof, **never** `verify_dataset.py`, which writes the receipt (line 221).
- **Pin Track B's own instruments:** a methodkit receipt over `verify_claims.py`, `leakage.py`, `runlog.py`, the prereg JSONs and `exp_*.py`, with the red witness: edit `SHINGLE` → receipt flips to VERIFIER-CHANGED. This closes the survey's named gap (changing scanner constants silently changes what old verdicts meant).
- **Ledger transplant:** wire `verify_dataset.py` / `ruler_noise.py` re-verify paths to append to a methodkit ledger so Track A's receipts stop being current-state-only snapshots.
- R-1 framing: machinery landed; formal discharge (eol normalization + one receipt regeneration under it + autocrlf probe) remains **the maintainer's explicit decision** — say "enabled," never "closed."

### WS-5: locallm science — two preregistered MPS experiments *(each ~1 day instrument work + <1 hr compute)*

**(a) Blockwise-Adam damage curve** (`locallm/optim8bit.py` + `locallm/adam_bound.py`), with all reviewer fixes applied:

- Bound constant is `C(β1,β2)·Σlr` with `C = max(1, (1−β1)/√(1−β2))` **= 1.0** at train.py's `betas=(0.9,0.95)` — not 3.16 — plus a decoupled-weight-decay displacement term for `wd=0.1`.
- Outlier injection **after** `clip_grad_norm_` (or inside the optimizer wrapper), pre/post norms logged; add an activation-injection arm so the natural activation-gradient coupling is represented.
- Vendor bnb 0.50.1's dynamic/udynamic qmaps from the Dell (hash-receipted) instead of writing linear absmax; quantize both moments for the parity arm; mirror `min_8bit_size` (locallm's 256-element layernorms stay fp32 in real bnb). Note `poscontrol/quantized_adam_emulator.py`, `adam_bound_scan.py`, `grad_witness_hook.py` already exist — extend, don't re-invent.
- Preregister the survey-null branch (massive activations are scale-emergent; 0.4M–19M may show none naturally) and the detection-margin refutation branch.
- Claim ceiling: "a controlled second-architecture demonstration the paper can cite as **partial** discharge of Limitation 3c" — full discharge needs the real-bnb anchor (see NEXT).

**(b) Regime-boundary sweep** (`exp_regime_boundary.py` + prereg), with the metric fixed:

- **Double-centered** per-bucket loss profiles (subtract bucket means and run means) — raw profiles are degenerate (bucket difficulty dominates, r≈0.99 everywhere) and the naive pilot gate would not catch it.
- Grid reshaped toward where from-scratch training actually breaks (1,2,4,8,12,16,24×; 40× kept as an expected-divergence arm), with "arm diverges" preregistered as a *stability* result, separate from functional disagreement.
- Honest deliverable: a locallm-native regime result bound into the README chain, plus the genuinely transferable piece — **calibration of the split-half Spearman-Brown disattenuation estimator** (when/why it exceeds 1.0 vs a many-replicate truth), which answers the paper's own r>1.0 caveat at `body-4.tex:88`. This is *not* F3 and does not locate the 8B boundary; write it as a companion study.
- Log the corpus's SUSPECT leakage verdict (content_frac 0.107) into `not_claimed`.

### WS-6: Metal-arm prep *(hours now; experiment gated on artifact recovery)*

Zero-regret staging for the re-execution arm on a third serving stack: install Ollama; pull `llama3:8b-instruct-q4_K_M` and check the blob against `sha256-8d2bf4416eb1…` (fallback: copy blob+manifest from the Dell's `~/.ollama`); pin a verifier ≤3.13 (`/home/me/.local/bin/python3.12` = 3.12.10 matches the live receipt; 3.11.9 via uv if paper-matching is preferred — decide in the prereg, never 3.14, under which the typing mechanism does not exist); time a 2-replicate unbanked null smoke and **size N from the smoke before preregistering fixed N**. The gating milestone is recovering adapter `sha256-4107cf60` from the Dell or the t box (`C:\Users\t\source\srlm-forge\`); if both are dead, re-scope honestly to the positive-control pair (GGUF `2cf7e8cc…` already on this Mac) and drop the +0.55 replication claim. Metal rows go to the new device-fingerprinted ledger, **never** appended to `data/ruler_noise.jsonl`.

---

## 3. NEXT — ubuntu-box, GPU 0 only

Sequenced; respects UBUNTU-BOOTSTRAP etiquette (PhD work outranks, uv 3.12.10, venv rule, resumable chains under gpuguard).

### D-1: Run 2 — the re-execution campaign *(the single most quotable open item; ~1 overnight)*

Re-scoped around the one thing verified as **not** done: no banked row anywhere retains a completion, adapter hash, or model digest, so Limitation 3a's arm ("A re-execution arm would settle it and has not been run") is still unrun and unrunnable on banked data.

- First: check whether the 21 `hc-seed` adapters (or `rep1`/`rep2` checkpoints) were retained on the Dell. If yes, zero new training; if no, 2–3 fresh seeds (<1 GPU-hour total; liveness smoke at `--max-steps 2`, never 1 — the warmup defect trains 1-step runs at lr=0).
- Preregister `prereg_track_a_run2.json` (run-1 schema): **re-execution as primary endpoint** — every typing-only NameError failure re-executed once with the import prepended, both verdicts banked per row; strict verdict retained alongside per the eval.py DECIDED note. Fresh same-session null under the `(version, platform)` pooling key from GREEN-WITNESS-D. Retain every raw completion + adapter/model digest per row (closes Limitations 8–9 going forward, and makes the import-emission vs annotation-suppression mechanism answerable post-hoc from 12,000+ rows — retiring the 15-draw wrong-template probe).
- Second motivation, stated plainly in the prereg: the 21-seed hc campaign in `ruler_noise.jsonl` is **unpreregistered exploration**; this program's own discipline demands the confirmatory run be the preregistered one.
- Dropped claims (already superseded, per the stale-OPEN-ITEMS audit): "first 8B run," "first 8B export" (exports ran ~25× to serve the Dell arms), "fourth hardware row" (RTX 6000 Ada is already in v15), "gives seed variance its slot" (21 seeds banked; WS-1 already decomposed it).

### D-2: Emulator anchor session *(half a day, GPU 0, shared with D-1 scheduling)*

Real `adamw_bnb_8bit` on the tiny locallm model at 2–3 g-sweep points, same device as the emulator, identical fixed gradient sequences, step-matched — the anchor that converts WS-5a's curve from emulated to demonstrated, and the only piece of 3c-discharge that requires CUDA. Vendor the qmaps here.

### D-3: Version matrix *(10–14 GPU-hours over several sessions)*

{PEFT 0.14.0 vs 0.20.0} × {bnb 0.45.0 vs 0.50.1} at pinned trl 0.12.2/transformers 4.46.3, **one torch build fixed across all cells** (2.5.1+cu121, the channel-logged original) with the Python-version delta named as residual. Corrected inference direction in the prereg: a commission-class cell isolates the varied pair *and* excludes OS-necessity; an all-healthy grid concludes only "library versions are not sufficient on Linux at this torch pin" — it can narrow to, never exclude, OS (a healthy Ubuntu cell is the TDR hypothesis's own prediction). Assays per adapter: adam-bound scan, `export_adapter.py --verify` 50,000× control, and a **new** residualized-31-task behavioral classifier (healthy centroid from the committed Table 2b/Appendix C record — `compare_adapters.py` is weight-space and useless here; build the classifier on the Mac before Dell time). Either outcome is a v16 section: kill the library axis, or first isolation of the anomaly.

### D-4: Ruler v3 *(conditional; ~15–20 GPU-hours)*

Gated on D-1/D-3 reproducing a within-ruler-v1 retrain gain on this stack, and preregister that gate. Reframed as the *third* instrument (the "never-built second instrument" OPEN-ITEMS entry is stale — the 31-task ruler is the second). Half-day tooling first: parameterize `build_ruler.py`/`ruler_noise.py` per instrument so ruler v1's frozen receipt is untouched. The 17 ruler-side mined tids (7 oss-only — decide strata in prereg) are a shortlist only; mandatory n=60 re-confirmation under the Dell's recorded verifier fingerprint. Add a same-session ruler-v1 anchor arm so the typing-share comparison isolates the task draw. Settle the drop-k=3 estimand decision in this prereg before any screening GPU time. Honest bound: same corpus, same language — this tests instrument-draw dependence, not the corpus/language half of Limitation 4.

---

## 4. The manuscript — what v16 gains, and the second paper

**v16 gains, in order of impact:**

1. **The re-execution measurement** (D-1, and the Metal arm if the adapter is recovered): converts the abstract's own caveat from bound to measurement — worded as "a re-execution arm has now been run, on [this stack]"; the published 48–58% figures stay bounds forever (those completions are gone; Limitation 9).
2. **Failure 8 repair landed** (WS-4): the paper gets to write its own wished-for sentence — "published digests reproducible off Windows for the first time" — via declared-dialect receipts, with F4/F8's withdrawn-claim embarrassments converted into a completed finding.
3. **The claim census appendix + erratum** (WS-3): every number labeled machine-verified/archival/withdrawn, opening with the live catch (the stale 5-of-40 retention disclosure — the null rows are back). Partially answers Limitation 12's self-review circularity: the checker is a fixed mechanical list any reviewer can run.
4. **Content-level disjointness sentence** (WS-2), anchored at `body-1.tex:59`/`body-4.tex:15`, bounded to one contamination mode.
5. **Version-matrix section** (D-3), either outcome.
6. **Limitation 3c partial discharge + the free adapter check productized** (WS-5a + D-2), with the corrected bound constant.
7. **Disattenuation-estimator calibration** (WS-5b) answering the r>1.0 caveat at `body-4.tex:88`.
8. Housekeeping the audits surfaced: fix the `body-2.tex:96` ("first experiment") vs `appendices.tex:282` (F3, demoted) inconsistency; give orphaned Table 4 its prose pointer; update F7's "repair prescribed" if effective-config recording lands with D-1.

**Second paper: yes, one, and it is the methods artifact.** WS-2 + WS-3 + WS-4 together are "the kit, transplanted": receipt engine with declared-dialect canonical hashing, append-only ledger, claim-binding with a measured catch-rate, prereg schema, red-witness discipline — *evaluated* by cross-gating two real codebases at 3M and 8B scale, with the port-without-retracting constraint as the non-obvious design story. Target: an artifact-track / methods venue. The damage curve (WS-5a + D-2) is a possible short workshop paper if the parametric curve is clean, but its natural home is a v16 section. The TRL/PEFT seed-ordering defect stays an appendix + upstream issue (finish the `main`-branch trace first), not a paper.

---

## 5. Repo and method mechanics

**Layout of the monorepo:**

- `locallm/` remains the public MIT subtree and gains `locallm/methodkit/` — the public repo ships the citable artifact; Track A imports from the subtree (private-depends-on-public; `sync_public.py` publishes `locallm/` only, so nothing at repo root is ever public). One copy of every file, per the merge principle.
- Track A stays at repo root, un-published, with its licence fences intact: **KodCode (CC BY-NC) never leaves this machine; AceCode (MIT) ships with attribution.**
- New Track A rows (Metal, Run 2, matrix cells) land in the new device-fingerprinted methodkit ledger. `data/ruler_noise.jsonl` stays byte-identical to the published record — it is a paper artifact now, not a live sink.

**Receipt policy:** the live schema-5 LF receipt is authoritative; methodkit reads it backward-compatibly; the CRLF digests in the paper are checkable history via the dialect field. **Receipt regeneration remains an explicit the maintainer decision** (UBUNTU-BOOTSTRAP rule), required only for the eventual schema-6 field carrying the pool-vs-ruler per-task leakage maxima — bundle that with the R-1 discharge decision so the receipt is regenerated once, not twice. Two standing traps, now documented: `verify_dataset.py` *writes* the receipt (use `require_verified` to check), and the memory note "srlm-forge provenance dialect" predates `c4290b4` and must not be re-imported as a CRLF-fixed-point design constraint.

**Method core (what unifies):** one prereg schema with a single canonical negative-scope field (retire the `what_this_CANNOT_show` / `not_claimed` split); receipts fingerprinting data + measurement code + interpreter, bypass-free, parse-don't-validate accessors with coverage tests; append-only ledgers with the qualifying verdict beside every number; red-witness-before-fix with the measurement recorded beside the repair; honest-limits stated first on every guard. Both tracks already practice all of it; methodkit makes it importable.

**What stays separate, and why:** the verifier/executor (`forge.py` and the SQL domain's runtime) stays Track A's — execution-grounded verdicts are the field site's subject matter, not shared infrastructure, and `domains/sql`'s forbidden-to-import-forge rule stands. locallm's trainer and experiments stay self-contained and beginner-runnable — the WS-2 gate must refuse on bad verdicts, not on missing setup. The paper's tex tree stays outside the repo; `verify_paper.py` bridges by path and pinned commit.

**Hygiene backlog (cheap, do alongside NOW):** prune `OPEN-ITEMS.md` — the "No Track A prereg" entry (closed 2026-08-02), the CRLF-receipt entry (superseded by the LF re-verify), the "export untested on 8B" and "no real-base run" entries (superseded by the Dell campaign), and the half-decided greedy-anchor entry (greedy-free landed; drop-k=3 remains genuinely open, decided in D-4's prereg). Pin `requirements.txt` (10 unpinned names; declare bitsandbytes). Finish the TRL `main` audit row.

**The graveyard — killed, and staying dead:**

- **"Ground-truth calibration of Track A's statistics" (locallm as a statistics surrogate).** Dead for four independent reasons: the quantity it wanted to measure by surrogate is already measured *in-system, better* (hc-seed01..25: 11 seeds × 40 replicates on the real instrument); the correction factor is a function of σ²_seed/σ²_replicate and does not transfer across systems — sizing the 8B run from a 3M char-model's ratio is exactly the assumed-not-measured input the program forbids; `analyze_run1.py` contains no TOST, so the surrogate would have certified code that had to be written anyway; and 30 shared-checkpoint seeds give seed-limited pseudo-replicated FPR bars — the very Dodge/Bouthillier error the program's own council cites against others. Its salvageable parts were extracted into WS-1 (stats_core + TOST + Monte Carlo + hc-seed decomposition) and are *better* than the original: zero training, real instrument. Any future proposal to "calibrate Track A's statistics with locallm training runs" should be answered by pointing at `data/ruler_noise.jsonl`'s hc-seed rows and this paragraph.

**Standing lesson from the review cycle, worth institutionalizing:** four of ten surviving proposals were written against a repo state that had already moved (the LF receipt, the merged null rows, the Dell campaign, the built second instrument). The program's own remedy applies to its planning documents too — **plans are claims; check them against the bytes before spending on them.** WS-3's manifest and WS-4's receipts are how that becomes mechanical rather than habitual.
