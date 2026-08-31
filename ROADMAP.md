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

The Track B `verify_claims.py` pattern aimed at `~/Documents/research/v15-arxiv/tex/`:

- `paper_claims.json` manifest: Table 1 → `analyze_run1.py` recomputation; MDE/N → `prereg_track_a_run1.json`; dataset facts → `dataset_gate.load_verified()`; concentration → `bank_concentration.json`; mutant survival → `test_adequacy.json`; ruler sha → `ruler_frozen.json`. Note t/p/CI live in `body-2.tex:28` and Appendix A, not in `tables.tex:26-27`.
- **Corrected expectations:** both Table 1 arms now verify from retained bytes (the 40 null replicates were merged back at commit `eb6ff4b`), so the checker's *first genuine catch is the paper's own stale 5-of-40 retention disclosure* (Appendix C, Table 1 note, F3) — a live, publishable erratum on day one, and better evidence for the thesis than the originally-planned "archival" demo.
- Hash rule: content→CRLF canonical for the paper's printed digests (`85fc0bdc…`, `15770d4d…`), with raw digest + platform recorded alongside — otherwise every hash check false-fails against the LF checkout.
- Recall calibration against the 2026-08-22 dossier: denominator = the **29 CONFIRMED** discrepancies annotated in/out-of-scope for digit-binding (not all 42; 5 are refuted, 3 pending, several are wording disputes). The v3–v9 drafts are Markdown, so budget the second extraction frontend as real work, not incidental.
- Pin the artifact state the manifest binds (named commit) and say so in the census appendix. Output classes: machine-verified / archival / withdrawn — with the archival class honestly smaller than first advertised.

### WS-4: Provenance core — `methodkit` *(3–5 days; merges "methodkit" + "Three-OS Verdict Invariance")*

The single most consequential design decision, written against the **post-`fd90f97` world** (the live receipt is schema 5, LF-dialect, `python 3.12.10`, and the gate already passes on this Mac via `SRLM_VERIFY_PY` — the old "Mac fails closed / CRLF fixed point" framing is stale, including the memory note that encodes it):

- **Declared-dialect receipts:** the canonical dialect is a schema-versioned *field of each receipt*, not a fixed CRLF constant. `methodkit` hashes `canonical(blob, receipt.dialect)`. The live LF receipt verifies unchanged with zero regeneration; the paper's printed CRLF digests survive as checkable historical values. Flagship test, parameterized both ways on one committed blob: `dpo_pairs_capped.jsonl` → `0bb9a659…` under `dialect=lf` (live receipt) and `85fc0bdc…` under `dialect=crlf` (paper). This is Failure 8's prescribed repair, landed — and it is *more* urgent than originally pitched, because the paper's printed digest currently dangles against the live receipt (exactly the "reads like tampering" failure the program documents), and default-config Windows clones now fail against the LF receipt: the dialect problem flipped platforms, it did not go away.
- **Placement:** `methodkit` lives **inside `locallm/`** (the public MIT repo ships the citable artifact; Track A imports from the subtree — private-depends-on-public, one copy of each file per commit `7ec4071`). It must read schema-5 receipts backward-compatibly; no `SCHEMA` bump, no regeneration — that decision stays maintainer-gated per `docs/UBUNTU-BOOTSTRAP.md`.
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

Zero-regret staging for the re-execution arm on a third serving stack: install Ollama; pull `llama3:8b-instruct-q4_K_M` and check the blob against `sha256-8d2bf4416eb1…` (fallback: copy blob+manifest from the Dell's `~/.ollama`); pin a verifier ≤3.13 (`~/.local/bin/python3.12` = 3.12.10 matches the live receipt; 3.11.9 via uv if paper-matching is preferred — decide in the prereg, never 3.14, under which the typing mechanism does not exist); time a 2-replicate unbanked null smoke and **size N from the smoke before preregistering fixed N**. The gating milestone is recovering adapter `sha256-4107cf60` from the Dell or the t box (`C:\Users\t\source\srlm-forge\`); if both are dead, re-scope honestly to the positive-control pair (GGUF `2cf7e8cc…` already on this Mac) and drop the +0.55 replication claim. Metal rows go to the new device-fingerprinted ledger, **never** appended to `data/ruler_noise.jsonl`.

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

**Receipt policy:** the live schema-5 LF receipt is authoritative; methodkit reads it backward-compatibly; the CRLF digests in the paper are checkable history via the dialect field. **Receipt regeneration remains an explicit maintainer decision** (UBUNTU-BOOTSTRAP rule), required only for the eventual schema-6 field carrying the pool-vs-ruler per-task leakage maxima — bundle that with the R-1 discharge decision so the receipt is regenerated once, not twice. Two standing traps, now documented: `verify_dataset.py` *writes* the receipt (use `require_verified` to check), and the memory note "srlm-forge provenance dialect" predates `fd90f97` and must not be re-imported as a CRLF-fixed-point design constraint.

**Method core (what unifies):** one prereg schema with a single canonical negative-scope field (retire the `what_this_CANNOT_show` / `not_claimed` split); receipts fingerprinting data + measurement code + interpreter, bypass-free, parse-don't-validate accessors with coverage tests; append-only ledgers with the qualifying verdict beside every number; red-witness-before-fix with the measurement recorded beside the repair; honest-limits stated first on every guard. Both tracks already practice all of it; methodkit makes it importable.

**What stays separate, and why:** the verifier/executor (`forge.py` and the SQL domain's runtime) stays Track A's — execution-grounded verdicts are the field site's subject matter, not shared infrastructure, and `domains/sql`'s forbidden-to-import-forge rule stands. locallm's trainer and experiments stay self-contained and beginner-runnable — the WS-2 gate must refuse on bad verdicts, not on missing setup. The paper's tex tree stays outside the repo; `verify_paper.py` bridges by path and pinned commit.

**Hygiene backlog (cheap, do alongside NOW):** prune `OPEN-ITEMS.md` — the "No Track A prereg" entry (closed 2026-08-02), the CRLF-receipt entry (superseded by the LF re-verify), the "export untested on 8B" and "no real-base run" entries (superseded by the Dell campaign), and the half-decided greedy-anchor entry (greedy-free landed; drop-k=3 remains genuinely open, decided in D-4's prereg). Pin `requirements.txt` (10 unpinned names; declare bitsandbytes). Finish the TRL `main` audit row.

**The graveyard — killed, and staying dead:**

- **"Ground-truth calibration of Track A's statistics" (locallm as a statistics surrogate).** Dead for four independent reasons: the quantity it wanted to measure by surrogate is already measured *in-system, better* (hc-seed01..25: 11 seeds × 40 replicates on the real instrument); the correction factor is a function of σ²_seed/σ²_replicate and does not transfer across systems — sizing the 8B run from a 3M char-model's ratio is exactly the assumed-not-measured input the program forbids; `analyze_run1.py` contains no TOST, so the surrogate would have certified code that had to be written anyway; and 30 shared-checkpoint seeds give seed-limited pseudo-replicated FPR bars — the very Dodge/Bouthillier error the program's own council cites against others. Its salvageable parts were extracted into WS-1 (stats_core + TOST + Monte Carlo + hc-seed decomposition) and are *better* than the original: zero training, real instrument. Any future proposal to "calibrate Track A's statistics with locallm training runs" should be answered by pointing at `data/ruler_noise.jsonl`'s hc-seed rows and this paragraph.

**Standing lesson from the review cycle, worth institutionalizing:** four of ten surviving proposals were written against a repo state that had already moved (the LF receipt, the merged null rows, the Dell campaign, the built second instrument). The program's own remedy applies to its planning documents too — **plans are claims; check them against the bytes before spending on them.** WS-3's manifest and WS-4's receipts are how that becomes mechanical rather than habitual.

---

## WS-7: The verifier gauntlet — multi-language verified pairs

**STATUS 2026-08-31 (pre-dawn):** six of seven tier-A kernels are LIVE in
`t/` — Dafny 4.11.0, Verus 0.2026.08.30, GNATprove FSF 16.1.0, Frama-C 33.0
(alt-ergo 2.4.3-free), Lean 4.33.1, Rocq 9.2.0 — with `t/run_all.py` showing
FULL AGREEMENT (real VERIFIED / twin REFUTED, flake-checked) on every task ×
kernel cell. Agda 2.8.0's ADAPTER is measured and landed (exit 0/42, bracketed
error names, --safe); its LOWERING is parked: the stdlib has no lia/omega
analogue, so the proof-synthesis template for the LIA fragment is a design
problem, not a typing task. Parked follow-ups: WP countermodel prover naming
(why3 lists `counterexamples` configs; -wp-prover spelling TBD), and the
per-goal gave-up-vs-countermodel refinement shared by SPARK and Frama-C.

**STATUS 2026-08-31 (ubuntu-box):** step zero is DONE — all six kernels
reinstalled no-sudo on the Dell after the machine wipe (pinned, hashed; see
`t/WITNESS-2026-08-31-dell.md`) and the full suite run there. The Verus
remeasure is discharged, after a second repair to the MALFORMED classifier:
the `error[` stderr match was itself vacuous against the bracketless
crate-name diagnostic, so REFUTED now requires the solver's own nonzero
errors count. The Rocq v1 lowering, recorded above as unfinished, lowers and
flips 10 of 11 as landed; its one remaining cell, count_matches, was a
non-terminating `t_merge` rewrite in the generated prelude (missing occurs
check, self-retriggering `replace`) and is fixed at the root. `t/run_par.py`
(cell-parallel driver, adversarially reviewed, cross-checked byte-identical
against `run_all.py`) cuts a full suite from 27 min to the slowest cell.

**STATUS 2026-08-31 (ubuntu-box, evening): 7 kernels, 77/77 FULL
AGREEMENT.** F\* is landed as the seventh kernel — SMT-track item 3 done:
official v2026.08.30 binary, taxonomy measured on the box before the adapter
was written, full column flips, adversarial skeptic reproduced it from
scratch and caught `[@@expect_failure]` as a verify-anything hole (now
banned; fix red-witnessed). WS-8's x86_64 question is answered in
`tup/X86-FEASIBILITY.md`: GO via KVM guest once the account joins the `kvm`
group; TCG measured ~14x as the fallback; rootless chroot measured dead.

**STATUS 2026-08-31 (adapter audit — the instrument turned on itself).**
Seven hostile agents, one per kernel, were told to make a FALSE theorem pass
through each adapter. They found ~38 holes, every one with a live probe.
Three classes: (1) acceptance mistaken for proof — empty files,
comments-only files, `verified==0` runs, and a Lean binary pointed at
`/bin/true` all returned VERIFIED, which reaches the HONEST pipeline, not
just adversarial input; (2) evadable lexical bans — word-boundary escapes
(`sorryAx`, `tadmit`, `assume_specification`), Axiom synonyms (`Parameter`,
`Conjecture`), pragma-versus-aspect forms, comment-hidden and
macro-expanded admits, an ACSL `axiomatic` block never banned at all;
(3) output-parse injection — rocq's closedness gate is a substring search,
so a decoy `Print Assumptions` on a trivial lemma prints the sentinel while
the real proof's audit is withheld; Lean falls the same way to
`#guard_msgs`. Plus six of seven adapters crashed on non-UTF8 input.

The repair inverts the trust model: **stop blocklisting bad mechanisms;
require positive evidence that the named obligation was discharged.** After
one hardening wave and an independent re-attack per kernel, **dafny, lean
and rocq are SOUND** (no probe scores a false VERIFIED; dafny survived 56).
**verus, spark, framac and fstar remain porous**, and the four survivors
share one root cause worth stating as a law: *semantic vacuity is not
detectable by regex.* `requires 1 == 0`, `Pre => (1 = 2)`, a content-free
`Post => (True)`, and a non-well-founded ACSL logic function all let the
solver honestly discharge an obligation whose hypothesis is unsatisfiable.
Dafny is sound precisely BECAUSE its adapter runs a semantic vacuity probe
(`--warn-contradictory-assumptions`) rather than a word list. The fix for
the rest is each kernel's own equivalent — `-wp-smoke-tests` for Frama-C
(already named in 7.4's known-bad-flags list as a default that must not stay
off), an `assert false` reachability probe for Verus, GNATprove's
inconsistent-precondition proof warnings for SPARK. F\*'s hole is different:
its positive-evidence counter greps stdout for `Query-stats`, which a
`print` in the source can forge, so the count must come from a channel the
source cannot write to.

The Dafny pipeline (`~/srlm-forge/dafny_verify.py`, `dafny_pairs.py`) is the specification: a five-way measured outcome taxonomy (VERIFIED / REFUTED / MALFORMED / VACUOUS / TIMEOUT), a deterministic resource budget with a hash-pinned toolchain fingerprint, flake-checking before any verdict is trusted, single-hint ablation kept only on a measured verified→refuted flip, spec mutation, permissive-only shipping, and headless no-sudo installs on macOS-arm64 and Ubuntu 24.04. Nine languages were dossiered and every dossier survived a hostile fact-check; all tiers below are post-correction (no tier was overturned, but several load-bearing details were — they are folded in here, not in the dossiers). Limits first: no Ubuntu install below was executed on the actual box except Dafny's; every "proven" claim is macOS-measured plus a verified self-contained Linux artifact, and step zero on the Dell is always to re-run the language's probe matrix there.

### 7.1 The matrix

| Language | Toolchain (pin) | Tier | Verdict taxonomy | Determinism | Corpus (shippable core) | One-line risk |
|---|---|---|---|---|---|---|
| SPARK 2014 | GNATprove FSF 16.1.0 tarball (bundles Why3 1.8.2, Z3 4.15.4, cvc5, Alt-Ergo — no COLIBRI); `--prover=z3 --steps=N` | A | Five-way measured (13-probe matrix, independently re-run); exit codes ambiguous — classify from phase errors + per-unit `.spark` JSON; `.spark` distinguishes countermodel from gave-up | `--steps` deterministic; fully self-contained tarball with published per-platform sha256 — best pinning story of the nine | SPARKNaCl (BSD-3), SPARKlib (Apache-2.0), spark_unbound (MIT); 4,422-test GPL suite local-only | Permissive corpus is an order of magnitude smaller than DafnyBench |
| Rust (Verus) | Verus release 0.2026.08.30.b432e82 (bundled Z3 4.16.0, Rust stable 1.97.1 via rustup) | A | Five-way measured via `--output-json` + rustc-JSON stderr; exit 0/1 only; rlimit-exhaustion hides inside the errors count — split by message text | `--rlimit` budget; `VERUS_Z3_PATH` + on-by-default solver-version check; every JSON run self-reports version/commit/toolchain | All-MIT: vstd, human-eval-verus (167 tasks; exclude `tasks/gpt/`), AutoVerus benchmarks, anvil, verified-storage | `assume`/`admit`/`external_body` verify anything at exit 0 — lexical ban on both halves, counted not dropped |
| F* | Official binary v2026.08.30 pinned per corpus; bundled Z3 4.13.3 via `--smt` + `--z3version`; `--report_assumes error` WITHOUT `--cache_off` (composed combination measured to fail every file — Prims' own axioms trip it) | A | Five-way measured incl. an end-to-end pair demo (7 flips + 1 survivor from one ulib file); both failure classes exit 1 — parse JSON diagnostics (19=refuted, 168/resolution=malformed, 335=vacuity); timeout shares error 19, split by message text | Same Z3 rlimit mechanism as Dafny (`--z3rlimit`×500k units), `--z3seed`, native `--quake` flake checker; three bundled Z3s make pinning mandatory | ulib+examples, HACL*, EverParse, steel, everquic (all Apache-2.0); FStarDataSet-V2 (CDLA-P-2.0, 54.4k definitions) | Frequent releases break corpora (FStar.Mul removed ~2026-04, not August) — F* version pinned per corpus, cross-version pairs never mixed |
| C (ACSL/Frama-C WP) | Frama-C 33.0 + Why3 1.8.2; Z3 (MIT) primary with alt-ergo-free 2.4.3 secondary — NOT opam `alt-ergo` 2.6.3, which is OCamlPro non-commercial; frozen why3.conf, `-wp-no-why3-detect` | A | Documented-measured, not yet executed: verdict lives only in `-wp-report-json` (exit 0 with unproved goals); `failed`=prover error→TOOL_ERROR, `invalid`=model-backed refutation, `unknown`=REFUTED, `stepout` distinct | `-wp-steps` is an explicitly machine-independent budget with its own verdict; pin `-wp-timeout` AND `-wp-smoke-timeout` (both default 2s wall) | ACSL by Example (MIT, maintained, targets 33.0); x509-parser BSD arm and Contiki-NG modules need porting | Three default-flag traps + the most fragile no-sudo install (opam `--disable-sandboxing`, source-built GMP, pre-existing gcc required) |
| Lean 4 | elan-pinned 4.33.1 (post-soundness-fix) + mathlib olean cache; leanprover-community/repl for throughput (Kimina server is stale and pins pre-fix v4.26.0 — do not adopt as-is) | A | Five-way measured + INCOMPLETE for holes; exit 0 ≠ verified (`hasSorry` gate, `#print axioms` allowlist); parse errors carry kind `[anonymous]` — text-match with parse-precedence, never kind-only | No SMT — architectural; `-DmaxHeartbeats` deterministic budget, but in-file `set_option` overrides the CLI (measured) — denylist required in v1 | mathlib4 (286k theorems), Compfiles, Lean Workbook, Batteries — all Apache-2.0 | Per-variant cost 10–100× Dafny without a resident-environment REPL; monthly toolchain churn invalidates receipts |
| Rocq (Coq) | opam `rocq-core.9.2.0` + `rocq-stdlib.9.2.0` (`rocq-prover.9.2.0` does not exist) + `rocq-mathcomp-boot.2.6.0` | A | Three-pass measured: `-vos` fail→MALFORMED, full compile fail→REFUTED, `rocqchk` axiom scan→VACUOUS vs VERIFIED (parse `* Axioms: <none>` — the section is always printed; rocqchk exits 0 even with axioms) | Architectural — no solver, 5/5 identical verdicts; only wall backstop is nondeterministic | MathComp core/fourcolor/odd-order (CeCILL-B), Iris/std++ (BSD-3); **analysis is CeCILL-C — local-only**; stdlib LGPL local-only | Ubuntu opam route hard-requires gcc (unconfirmed on the Dell) + `--disable-sandboxing`; per-corpus loadpath engineering |
| Agda | Official 2.8.0 single binary (one sha256 — no solver exists) + stdlib v2.4 at commit, `--safe` always | A | Measured: exit 0 / 42 / 251 + stable bracketed error names; INCOMPLETE class for holes; `--safe` refuses postulates and pragma smuggling ex ante with named SafeFlag* errors | Architectural; RTS heap cap (`-M`) as deterministic resource bound; single-binary fingerprint | agda-stdlib (MIT), cubical (MIT+BSD-3), agda-unimath (MIT), agda-categories (MIT) — ~960k LOC | Ablation unit is a syntactic step/clause, not a line — `find_hints` rewrite; hint density at scale unproven (the pilot is the tripwire) |
| Haskell (Liquid Haskell) | LH 0.9.14.1.1 on GHC 9.14.1 + **liquid-prelude** (omitting it breaks proof combinators) via package-env; PATH-shim-pinned Z3 4.15.8/4.16.0 | B | Rebuilt by hand: GHC exits 1 for everything — two-pass compile + message-class parse; `--json` in plugin mode is the highest-leverage unknown | No native rlimit — wrapper shim with cumulative per-module Z3 budget; solver `unknown` must be reclassified TIMEOUT from the shim log | LH test suite (BSD-3); benchmark suites per-suite allowlist ONLY — GPL hmatrix is vendored beside them under `tests/benchmarks/` | Three contract pillars (taxonomy, budget, vacuity) all custom; full GHC pipeline per variant |
| Whiley | wyc 0.10.18 + wyboogie 0.4.8 (`--noverify`) → raw Boogie 3.5.7 `/rlimit` + Z3 4.14.1 | B | Five-way from three stages + stdout regex — Boogie exits 0 on every outcome incl. parse errors; `/smoke` for VACUOUS, Boogie-level havoc for weak specs | Same substrate as Dafny (Boogie rlimit + PROVER_PATH), measured stable | Whiley2Boogie tests (Apache-2.0, ~1409 verifying programs); STD.wy is Apache-2.0 (dossier wrong) | Frontend dormant since 2022 — any bug is fork-and-own; hundreds of pairs, not thousands |

### 7.2 Rollout order

The criterion is stated by the contract: a language enters only when its five-way taxonomy is measured (not documented) and its no-sudo install is proven. Proof assistants are a separate sub-track because "verified" there means kernel-accepted proof term, REFUTED means ill-typed/unsolved rather than SMT-could-not-prove, and mixing those pairs untagged with SMT pairs changes what the preference signal rewards.

**SMT track:**

1. **SPARK** — the only candidate whose entire probe matrix was independently re-run by the hostile check from a hash-verified tarball; per-platform sha256 published in the Alire index; self-contained tarball needs nothing from apt. First step runs on the Dell directly.
2. **Verus** — full five-way measured on the current release, all-MIT corpus, rustup+zip install; its two gaps (undiscriminating exit codes, rlimit-out folded into errors) close in the harness and both closures were measured.
3. **F*** — the richest measured pair demo of the nine, but it pays for it: JSON-only classification, per-corpus F* pinning, and the corrected invocation (drop `--cache_off` from the reward run; use `--cache_off` minus `--report_assumes` only for byte-identical flake re-runs).
4. **C/ACSL** — tier A on paper, but the only A whose taxonomy has not been executed; sentinel-file re-measurement is mandatory before `framac_verify.py` ships constants, the prover pin must be the corrected free stack, and the install is the most fragile of the A tier.

**Proof-assistant sub-track:**

5. **Lean 4** — measured taxonomy, huge Apache corpus, one-curl installs on both platforms. v1 ships with the `set_option` denylist and parse-precedence classifier or not at all; throughput work (REPL) follows, not precedes.
6. **Agda** — fully measured taxonomy and the cleanest no-sudo story (one static binary), but gated on the 50-file stdlib pilot: if step/clause/rewrite ablation yields too few flips, the syntax-aware `find_hints` rewrite is not worth it. Linux binary is docs-verified only — smoke-test first.
7. **Rocq** — measured three-pass gate and the strongest vacuity instrument of the nine (independent kernel re-check), but gated on: gcc confirmed on the Dell, corrected opam pins, and acceptance of ssreflect dialect skew in the shippable corpus.

**B tier, opportunistic only:** Liquid Haskell after one measurement session resolves the `--json` plugin-mode unknown; Whiley only on idle capacity — everything is proven but the ceiling is low and the frontend is unmaintained.

### 7.3 The adapter interface: `verifiers/<lang>.py`

What `dafny_verify.py` + `dafny_pairs.py` generalize to. One module per language, stdlib-only, importable by both the system Python and `.venv-train` (the dataset_gate rule). Each adapter must supply:

- **`Outcome`** — the five core outcomes plus `TOOL_ERROR`, extended only by measurement (Lean/Agda add `INCOMPLETE` for holes; SPARK may separate flow-analysis failures). Invariants: `ok=True` only for VERIFIED; TIMEOUT (including deterministic resource-out) is never folded into REFUTED; any unlisted diagnostic is TOOL_ERROR, never evidence.
- **`toolchain_fingerprint(budget) -> dict`** — sha256 of every binary in the verdict path (frontend, solver(s), and runtimes where present: JVM, dotnet, GHC), pinned library identity (stdlib commit, `.vo`/`.agdai`/olean cache), the budget, and the full flag list. Hardening flags (`--report_assumes error`, `-wp-smoke-tests`, `--safe`, `--warn-contradictory-assumptions`) live in the fingerprint; a run without them is a different, weaker instrument.
- **`verify_source(source, budget) -> Result`** / **`verify_path(...)`** — fresh temp dir per candidate, always: this one pattern defeats every cache trap found across the nine (Dafny obj reuse, gnatprove sessions, F* `.checked` digest hits, GHC recompilation avoidance, Agda `.agdai`). Classification constants cite measurements in the docstring, per house discipline.
- **`flake_check(source, n=3, budget) -> dict`** — n independent runs, verdict distribution. Mandatory before trusting any single verdict; mandatory cross-platform for near-budget pairs (heartbeat/step counts drift across arch).
- **`pair_verdict(chosen, rejected, budget) -> dict`** — chosen must be VERIFIED (never vacuous), rejected genuinely REFUTED. Refuses rejected-that-verifies, MALFORMED-as-rejected, and any half containing the language's trust holes (`assume`/`admit`/`magic`, `pragma Assume`, `postulate`, `Admitted`, `sorry`, `external_body`, option-pragma smuggling) — counted, not silently dropped.
- **`spec_strength(source, budget) -> dict`** — the weak-spec oracle where a body/spec split exists (Dafny havoc, SPARK `Import` function, F* `assume val` havoc, Verus `external_body` havoc, WP `any_int`, Boogie-level `havoc` for Whiley). Where the statement is the spec (Lean/Rocq/Agda) it is replaced by signature pinning plus trivial-arsenal/exfalso probes. Either way the function exists and reports weak/adequate/unchecked — silence is not a pass.
- **Pairs side** (`verifiers/<lang>_pairs.py`): `find_hints` with the language's ablation unit (whole line for Dafny/F*/Verus/LH/SPARK pragmas; period-terminated sentence for Rocq; step/clause/rewrite for Agda; tactic line or simp-list element for Lean), `drop_unit`, `pairs_from_file`, `subset_pairs_from_file` with budget accounting, `generate`/`write_jsonl`.

Acceptance rule for any new adapter: the language's measured probe matrix becomes its unit-test suite, and the survivor rate (the 26.9% analogue) is re-measured on that language's corpus before a single pair is minted. The Dafny numbers do not carry across; nothing is projected from them.

### 7.4 Not worth doing

- **Prusti.** Master and releases frozen since 2024-03, pinned to a 2023 nightly rustc, JVM+Viper stack. Verus wins on every axis. If Verus ever stalls, creusot/Kani need their own dossiers (Kani is bounded model checking — different verdict semantics, not a drop-in).
- **WyTP** (Whiley's native prover) — dead since 2020/2021. Boogie is the only path.
- **Kimina Lean Server as-is** — stale (~7 months), default-pinned to a Lean that predates the 2026 kernel soundness fixes. Drive leanprover-community/repl directly or fork-and-validate.
- **Exit-code-only classifiers, anywhere.** Dafny is the only language of the ten with a discriminating exit-code split. Every other adapter that shortcuts to exit codes silently merges MALFORMED into REFUTED or vacuous into VERIFIED. This is a standing code-review refusal on every port.
- **Statement-mutation pairs in Lean/Agda sold as proof pairs.** A mutated statement with a kept proof is an autoformalization/spec-writing pair — a different task. Proof-side mutations (lemma swap, rw flip, step deletion) mint the proof pairs.
- **Directory-glob corpus ingestion.** Twice the hostile checks caught permissive suites sitting beside GPL/unlicensed material in the same tree (LH `tests/benchmarks/` vendors GPL hmatrix; Whiley's WyBench is unlicensed). Per-suite allowlists only.
- **Known-bad flags:** F* `--proof_recovery` and `--n_cores >1` (the unsoundness issue closed in 2019, but there is no reward-path upside); SPARK `--level` ever and `--replay` in the gate; Frama-C defaults unpinned (2s wall timeouts, smoke off, prover auto-detect); Verus `--num-threads` unpinned; opam `alt-ergo` 2.6.3 (non-commercial license on the pipeline itself).
- **Nix, apt, or anything needing sudo on the train box.** Every recommended install above is a pinned tarball/zip, rustup, elan, ghcup, or opam `--disable-sandboxing` into `~/.local` — kept away from the provenance venv per the standing train-box rule.

### 7.5 Licensing appendix

Standing rule: shippable means permissive. Non-permissive corpora are usable locally for measurement; derived pairs never ship from the MIT repo (the CC BY-NC incident is the precedent).

**Shippable (permissive, verified at source):**

| Corpus | License |
|---|---|
| F* ulib + examples; hacl-star; everparse; steel; everquic-crypto | Apache-2.0 |
| FStarDataSet-V2 (HuggingFace) | CDLA-Permissive-2.0 |
| SPARKNaCl | BSD-3-Clause |
| SPARKlib | Apache-2.0 |
| spark_unbound | MIT |
| Whiley2Boogie tests; WhileyCompiler tests | Apache-2.0 |
| STD.wy (corrected — LICENSE in-tree since 2022) | Apache-2.0 |
| ACSL by Example | MIT |
| ANSSI x509-parser (BSD arm; archived, porting cost) | dual BSD/GPL-2.0 |
| Contiki-NG verified modules (per-fork annotation check) | BSD-3-Clause |
| Verus: vstd/examples, human-eval-verus (excluding `tasks/gpt/`), verus-proof-synthesis, anvil (MIT text verbatim), verified-storage, verismo, verified-ironkv, verified-node-replication | MIT |
| LH test suite; six named benchmark suites via per-suite allowlist (bytestring, vector-algorithms, esop2013-submission, icfp15, stitch-lh, cse230) | BSD-3 / MIT |
| liquidhaskell-tutorial | MIT |
| lh-workshop (corrected from "unverified"; eyeball LICENSE on ingestion) | BSD-3-Clause |
| mathlib4; Compfiles; Lean Workbook; Batteries | Apache-2.0 |
| miniF2F-lean4 (corrected: yangky11 fork is MIT; openai Lean folder Apache) | MIT / Apache-2.0 |
| LeanDojo Benchmark 4 (attribution required; prefer regenerating from mathlib) | CC BY 2.0 |
| MathComp core; fourcolor; odd-order | CeCILL-B |
| std++; Iris | BSD-3-Clause |
| agda-stdlib; agda-unimath; agda-categories | MIT |
| agda/cubical | MIT + per-file BSD-3 |

**Local-only or excluded:**

| Corpus | Why |
|---|---|
| FStarLang/pulse | No license file detected — all-rights-reserved until clarified |
| mitls-fstar | Custom license, SPDX NOASSERTION |
| AdaCore/spark2014 testsuite (4,422 tests) | GPL-3.0 — the volume corpus, local calibration only |
| spark-by-example | Unlicensed |
| Marmaragan; experimental-agentic-verified-software | Mixed/unverified terms — methodological references only |
| WyBench | Unlicensed — excluded even locally so no pair can trace to it |
| Frama-C WP regression suite (source tarball) | LGPL-2.1 |
| VerKer | GPL-3.0 (and AstraVer-targeted) |
| LH `tests/benchmarks/` outside the six allowlisted suites (hmatrix, nofib, xmonad, …) | GPL and mixed vendored code — never glob the directory |
| Rocq standard library | LGPL-2.1-only |
| CompCert | INRIA non-commercial — the exact CC BY-NC analogue |
| math-comp/analysis (corrected — dossier wrongly grouped it with CeCILL-B siblings) | CeCILL-C (weak copyleft) |
| Software Foundations | Admitted-riddled skeletons + authors' do-not-post-solutions request |
| the1lab/1lab | AGPL-3.0 |

---

## The far field

Direction, not tasks. Measured costs stand beside each entry so ambition never
impersonates a plan; nothing here reorders NOW or NEXT.

- **The provable-output model.** The training loop's reward becomes "a proof
  kernel accepted it," across every language WS-7 admits. What this makes
  provable is each emitted artifact — the model itself is not thereby a proven
  object; proving properties of the network is a different research program,
  and the writing never blurs the two.
- **t.** One spec interlingua over the WS-7 adapters — write a task once, lower
  it to Dafny / F* / SPARK / ACSL / Verus / LH, collect N independent kernel
  verdicts; cross-verifier disagreement becomes an instrument finding, this
  program's own genre. Prior art: Why3 (one spec language, many provers) and
  Viper (an intermediate verification language many frontends target). Trust
  path if t ever grows its own checker: CakeML-style — the checker is verified
  inside an established kernel (Rocq or Lean). A homemade language certifying a
  homemade system is two unaudited instruments signing each other's receipts,
  and it is refused here in advance.
- **The reproducible substrate.** Nix/Guix closures are the receipt discipline
  applied to the operating system — a content-addressed hash of the entire
  dependency graph, and D-3's version-matrix cells become one-line derivations.
  Guix's full-source bootstrap is the serious answer to trusting-trust. Slots
  behind WS-4; the receipts learn to record a closure hash.
- **An OS in t.** The measured price of one verified microkernel with mature
  tools and a team: seL4 — 8,700 lines of C, ~200,000 lines of proof, ~20
  person-years. It stays on the horizon until there is a team. The
  LFS-with-receipts build begun 2026-08-31 (Lima VM on the M5 Pro; every
  tarball sha256-manifested, every build command book-extracted and logged) is
  the pedagogical rung under this — a fully witnessed substrate, not a
  verified one, and labeled accordingly.

---

## WS-8: RESCOPED — tup is VM-native by decision (2026-08-31)

The four gaps this section used to cost out (generic kernel, initramfs,
firmware, installer) are **deleted scope, not open work**. tup only ever runs
virtualized — including on the Dell, where it runs as a KVM guest on Ubuntu —
so bare-metal engineering had no consumer. The decision and its consequences:

- A VM-only distro ships a **disk image**, not an ISO with an installer.
  `tup/release.sh` produces qcow2/vmdk/vdi with hashes, and refuses to ship
  a qcow2 that has not reached `tup login:` on a serial console.
- The kernel keeps its compiled-in virtio set plus the SATA/e1000 fallbacks
  defconfig already gave it; VMware/VirtualBox should boot via those paths but
  are labeled UNVERIFIED until someone witnesses one.
- Witnessed so far: QEMU/hvf on macOS (20 s to login), QEMU/TCG on Ubuntu
  with no KVM at all (40 s) — the worst-case host, measured.
- Still real from the old list: the **x86_64 build** (same driver, x86 book)
  for the Dell as pinned verifier/analysis environment. Training stays on the
  Dell's host OS where CUDA lives.

## WS-9: going public — the checklist before the switch is flipped

The repository is private today and is intended to go public when the ISOs
exist. Publication is not reversible in the way people assume: history is
published too, and a repository that was public for an hour is public
forever. So this is a checklist, run BEFORE the flip, not after.

**Already clean, verified 2026-08-31 by scanning tracked files and full
history:** no API keys, tokens, or private keys anywhere; no KodCode-derived
data tracked (the CC BY-NC set exists only locally, as OPEN-ITEMS requires);
no collaborator names or institutional email addresses in tracked files.

**Three things that are NOT clean, and what to do about each:**

1. **65 files sit in history that were untracked for a reason** — the 61
   council reports and transcripts, the operating-protocol brief, the
   handoffs, the method-kit pointer. Gitignoring them stopped future commits;
   it did not remove them from past ones. Going public publishes all of it.

2. **One line in history reads badly out of context.** An early note describes
   "run the loop unattended without elevation prompts" — a
   throwaway phrasing about an unattended local build loop, but in a public
   repository belonging to someone doing security research it is a sentence
   that will be quoted without its context. It is in history, not in the tree.

3. **Fourteen manuscript files are tracked**, v10 through v15 of an
   unpublished paper. Publishing them is a real decision about priority and
   preprint norms, not an accident to discover afterward.

**The recommended shape, which matches how this project already works:** do
not scrub and flip. Publish a NEW repository containing only what tup IS —
`t/`, `tup/`, `locallm/`, README, ROADMAP — and keep this one private as the
working record. `sync_public.py` already implements exactly this pattern for
locallm: a whitelist, a forbidden-term abort, and a refusal to publish
anything mentioning the channel. Extending it to publish the distro and the
language is a day of work and it inherits the safety property that a history
scrub cannot give you: **the private record never had a public commit to
scrub in the first place.**

The alternative — `git filter-repo` over this history, then flip visibility —
is possible and is strictly more dangerous, because it depends on having
enumerated every sensitive path correctly the first time.
