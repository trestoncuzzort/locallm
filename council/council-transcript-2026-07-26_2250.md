# srlm-forge Council — Full Transcript, Activation #11

2026-07-26 ~22:50. DIRECTIVE-triggered (watcher task `bkk3n3jtj`). Follow-up round after last round's phase-blind sampler bug was fixed with winnowing, and the fast LR-width profile shipped.

---

## 1. The DIRECTIVE (verbatim, key parts)

> ASK — THE SAMPLER IS FIXED AND THE FAST PROFILE IS SHIPPED. I AM NOW GOING TO BUILD YOUR FINDING 2 (PERMUTATION NULL) AND FINDING 3 (NOISE FLOOR), AND I HAVE ONE QUESTION ABOUT EACH BEFORE THEY HARDEN.
>
> Q1 [PhD]. B and the exact p-value interact: the smallest attainable p is 1/(B+1), so a budget-sized B silently caps the strongest claim the tool can make. What is the right behaviour when the budget only affords, say, B=20 (minimum p=0.048)? I lean toward reporting the p-value with its floor stated, but this is a statistics call.
>
> Q2 [Expansionist, PhD auditing]. Should the SHIPPED default be the 13x1 total-floor design, with the 20-run decomposition available behind a flag? Or does shipping the cheap one by default quietly teach users that the decomposition does not matter?
>
> Q3 [Contrarian, PhD auditing]. Blunt question about my own work. The fixed-stride sampler shipped, was published, was described in a README as the number to trust, and was wrong 9 times in 10 for a month of project time. It was caught by you reading code, not by anything I built. What SHOULD have caught it?
>
> CLOSED-CLASS CLAIM + RED WITNESS: verbatim duplication is now detected regardless of byte offset. RED (fixed-stride): 1/10 detected. GREEN (winnowing): 10/10, 100.0% at every offset, 11,759 fingerprints (0.16s) vs ~54,900 before.

---

## 2. The five style advisors — raw responses (banked)

### Contrarian

> **THESIS:** The sampler bug hid because a correlated-but-different signal (line overlap) happened to catch the same cases, creating an illusion of correctness — names a general bug class ("correlated signal masking") worth watching elsewhere.
>
> `[VERIFY]` whether the new winnowing fingerprinter has its own hidden assumptions (collision rate, minimum run length).
>
> **Q1:** report p with floor stated, but reframe explicitly — "budget exceeded, this result is not comparable to smaller-corpus runs."
> **Q3:** both a process gap AND evidence of a recurring pattern — what other detectors silently rely on "if method A fails, method B catches it"?

*(The PhD: the specific mechanism was checked against the actual pre-fix code and found wrong — there was no redundant path in the decision logic at all. But his `[VERIFY]` flag on the new fingerprinter's collision rate was exactly right — see the round's headline finding.)*

### First Principles

> **THESIS:** Q1's three-option framing is a false trilemma — the p-value floor IS the measurement, not a shortcoming.
>
> Q3 reframe: not "what test would have caught THIS bug" but "what CLASS of claim needs self-testing by default" — any claim positioned as a decision-gate, defined by position in the system, not by the specific failure mode.
>
> **Direct answers:** Q1 — report p with resolution-limit line. Q3 — any detector gating downstream decisions needs self-testing as standard.

*(The PhD: adopted, with an exact derived boundary rather than a soft "state the limit" — see finding 3.)*

### Expansionist

> **THESIS:** Q2's "pick one default" is a false binary — propose progressive disclosure: report the cheap 13x1 result immediately, run the fuller 20-run decomposition in the background, upgrade the report when it lands.
>
> Extends the idea to Q1 too — report the capped p now, keep permuting in the background, stream updated values.
>
> `[VERIFY]` whether the tooling architecture even supports async/background reporting.

*(The PhD: verified the architecture DOES exist — studio.py's TrainWorker/queue pattern — but ruled the idea wrong for the CLI specifically, where a number that changes after being copied into a log violates the project's own preregistration discipline. Good idea, wrong surface.)*

### Outsider

> **THESIS:** The round is optimizing tradeoffs (Q1/Q2) while still recovering from a verdict engine proven unreliable (Q3) — and Q3's framing is subtly defensive, sidestepping the plainer lesson that ONE hand-crafted synthetic test (duplicate content at offsets 0/100/500/1000) would have caught it and nobody wrote it.
>
> Notes human code review worked here but is "luck, not testing infrastructure."
>
> **Q3 direct:** the shape of test that should have caught this is "embarrassingly specific" — an offset-sweep smoke test, not sophisticated theory.

*(The PhD: tested this exact proposed suite against the buggy code. It passes — all four offsets are multiples of the sampler's stride. This is the round's single most decisive result — see finding 2.)*

### Pragmatist

> **THESIS:** Concrete, buildable answers to all three.
>
> - Q1: exact proposed output — `p = 1/21 = 0.0476 [floor = 0.0476] — CANNOT CONFIRM CONTAMINATION`; refuse the verdict (not just caveat) when the floor exceeds the alpha threshold.
> - Q2: ship 13x1 as default, add a `--full-decompose` flag.
> - Q3: concrete test pattern — `test_detector_offset_phase_invariance`, parametrized on byte offset and seed phase, run in CI as a contract for every detector.
>
> **Monday morning:** write this test file, parametrized on duplication size and offset, commit to CI.

*(The PhD: the "refuse, don't just caveat" instinct was right and became the actual recommendation, with an exact derived threshold rather than an example number. "Commit to CI" doesn't survive audit — zero test infrastructure exists in this repo.)*

---

## 3. The PhD — closing pass (full, reproduced verbatim from the tool output)

*(All measurements below run live on this machine, this session. Zero repo files written. Probe scripts in scratchpad.)*

### Corrections to the round

**C1 — the Contrarian's "correlated signal masking" mechanism is factually wrong about this code.** Verified via `git show` on the pre-fix commit: the verdict property read `shingle_frac` alone; line overlap and doc overlap were printed but never consulted by the decision. No redundant code path existed. The masking happened in the human reading the report, not in code. This changes the prescription: a self-test must assert on `Report.verdict` and the exit code, not on a sub-metric that happens to correlate with it.

**C2 — the Outsider's specific proposed test would have PASSED on the buggy code.** Measured, old sampler, 200-char verbatim duplicate: the Outsider's offsets (0/100/500/1000) detect at 100% on ALL FOUR — every one is a multiple of `STRIDE=10`. The Pragmatist's offsets (0/13/997/random) detect at 100%/0%/0%/0% — 3 of 4 correctly fail. Across offsets 0-29, only `{0, 10, 20}` detect at 100% and the other 27 detect at 0%. This is the round's most important measured result and decides Q3 empirically.

**C3 — live, unflagged bug at exactly the scale Q1 is about.** `crc32` is too narrow for the winnowing fingerprinter and winnowing's minimum-selection makes it ~9x worse than a naive analysis predicts. Measured on 1MB of random text: mean hash value is 0.5002 of the full range, but selected (minimum) fingerprint mean is 0.0556 — a 9.0x collision inflation. False overlap on two independently-generated, genuinely-clean corpora: 0.0078% at 500KB rising to 0.0706% at 4MB; extrapolated, a corpus with zero real contamination crosses the shipped `SUSPECT=0.05` threshold at roughly 500MB on hash collisions alone. Fix: swap `crc32` for `blake2b` (64-bit digest) — verified same fingerprint count (38,348 vs 38,326), false overlap drops to 0.0000% at every measured size. One-line fix. Note: this doesn't invalidate the permutation-null's p-value (the collision floor appears identically in observed and permuted statistics), but it does invalidate the printed raw fraction the docstring calls "the one to trust."

**C4 — the 74-char guarantee is true, but the docstring omits a real regression.** Measured: 74 chars → 100% detected, 73 → 99%, 60 → 59%, 50 → 4%, while the OLD fixed-stride sampler detects 40% at length 50. Winnowing buys phase-invariance by giving up short-run recall — strictly worse below ~60 characters. Docstring reads as unconditional dominance; should carry the measured curve. Independent confirmation the implementation matches the paper: measured fingerprint density 7.65-7.72% vs. winnowing's predicted 2/(w+1) = 7.7%.

**C5 — the "round 7 mutation-testing" callback is misattributed.** The phrase lives in `council-report-2026-07-25_0317.md`, headed "Pass #3," not round 7, and referred to the DPO track's injected coding-task unit tests (a track since abandoned), not this toolkit's own source. The analogy still applies — arguably harder than claimed — but don't cite it as a previously-queued engineering item; it wasn't one.

**C6 — the Pragmatist's "commit to CI" prescribes infrastructure that doesn't exist.** `git ls-files` returns zero test files, zero conftest, zero workflow YAML, no `.github/`; pytest/hypothesis/mutmut are absent from `.venv-train`. Three build steps away, not a Monday morning. The Outsider is right about sequencing even though wrong about the specific test.

**C7 — §29's "block only on the expensive-to-reverse" is being read too permissively for Q2.** A noise floor is the denominator of every future claim; a default that biases it low bakes into published results by construction. This is squarely in the exempt-from-ship-fast category, not outside it.

**C8 — a units slip in Q1's framing.** "B=20 → min p = 0.048" is actually 1/21 = 0.0476. And the shipped `SUSPECT=0.05` is a fraction of overlapping fingerprints, not a significance level — the Pragmatist's proposed output line conflates the two; keep them lexically distinct in any implementation.

### Q1 — analysis and recommendation

The statistical fact that dissolves "refuse vs. caveat": the permutation estimator is exactly valid at ANY B (Phipson & Smyth 2010, abstract verified: "valid for any number of permutations and samples"). A small B is underpowered, not wrong. But there's a hard, derivable feasibility boundary: min p = 1/(B+1) ≤ α ⟺ B ≥ 1/α − 1. At α=0.05, B≥19; below that, rejection at level α is impossible regardless of the data. A 2026 preprint (Cha, Lee, Schrab & Kim, arXiv:2605.03886 — single preprint, not peer-reviewed, flagged accordingly) proves power is non-monotonic in B and that B where (B+1)α is an integer is a local power maximum — meaning the executor's own example, B=20, is actually a worse choice than B=19 (cheaper AND more powerful). Also: the "10 minutes at 100MB" budget concern in the DIRECTIVE was computed at B=200; the real feasibility floor (B=19-99 for realistic α) costs 1-5 minutes, not 10 — the framing overstated its own problem.

**Recommendation:** below the feasibility floor, print `NO VERDICT`, exit code 2, explain the exact arithmetic and both remedies (more permutations, or a weaker α) — never print CLEAN. At or above the floor, print the p-value with its floor stated on every run, including rejections. Default B to the smallest value at or above the feasibility floor with (B+1)α an integer. Use three exit codes, not two — the current binary trustworthy/not collapses "clean" and "couldn't tell," the same failure shape as the sampler bug.

### Q2 — analysis and recommendation

Architecture claim verified: `studio.py`'s `TrainWorker(threading.Thread)` + queue + `self.after(100, self._drain)` pattern is real and already used twice. But that makes progressive disclosure cheap in the GUI, not the CLI — a CLI number that changes after being copied into a log is the exact failure this project's preregistration discipline exists to prevent. More importantly: neither proposed design named whether the cheap "13 runs" holds seed FIXED (biased low, excluding init-seed variance — the exact failure ruled out last round) or randomizes it too. Fix costs nothing: randomize both split and seed together across the same 13 runs (Bouthillier et al. 2021, primary-source verified: "adding more sources of variation... approaches the ideal estimator at 51x less compute").

**Recommendation:** default = 13 runs with BOTH split and seed randomized (not fixed-seed), reporting the total noise floor with a one-line pointer to `--decompose` (10×2, ~5 min) named in the DEFAULT output text, not just `--help`. Do not build progressive disclosure into the CLI; revisit for the GUI where the architecture is already free.

### Q3 — analysis and recommendation

Both camps half right. The Outsider is right that zero test infrastructure exists and that catching this via code review was luck — but his own proposed test (C2) would have passed on the buggy code. The real principle: when an implementation parameter (stride, window, block size) could align with a test-input parameter, the input must be chosen adversarially or randomly, never by hand. Real, citable literature exists for the general class: Voas 1992's PIE model (a fault must be Executed, Infect the state, Propagate to output — here, propagation failed into a human, not a redundant code path, sharpening C1's correction), the "oracle problem" (Barr et al. 2015 — no ground truth exists for an arbitrary corpus's true contamination), and metamorphic testing (Chen et al. 1998, surveyed Segura et al. 2016) — built exactly for the no-oracle case; "prepending N bytes must not change what's found" is a textbook metamorphic relation.

**Recommendation:** write `localllm/test_detectors.py` — no framework, ~40 lines, runnable directly (matches the project's "torch-only" identity). Three tests: (1) phase-invariance using a MIX of round-number and `random.Random(0)`-drawn offsets, asserting on the scanner's verdict/exit code, not a sub-metric; keep the old buggy sampler in the file as a permanent regression oracle the new test must fail against. (2) no-false-positive-at-scale on two independent clean random corpora (currently fails with crc32, passes with blake2b-64 — C3). (3) infeasible-B-never-reads-CLEAN (Q1's interlock). Generalize step 1 into a reusable `assert_phase_invariant(detector_fn)` helper applied to every future detector. Mutation testing (mutmut on leakage.py) is the right eventual step, not the next one — there's no suite yet to measure.

### Citations, with verification notes

Primary-source verified this round (fetched, quoted): Phipson & Smyth 2010 (abstract-level; the exact formula itself has now failed body-level extraction twice across two rounds — flagged, not fully closed), Cha/Lee/Schrab/Kim 2026 (HTML fetched; single unreviewed preprint), Bouthillier et al. 2021 (abstract; body-level ordering carried forward from round 9's verification). Search-level/bibliographic only, none load-bearing: Voas 1992, Knight & Leveson 1986 (checked and found NOT to apply to this incident), Chen et al. 1998, Segura et al. 2016, Barr et al. 2015, Schleimer/Wilkerson/Aiken 2003 (independently corroborated via measured fingerprint density matching the theoretical prediction).

Repo claims verified at the byte: `studio.py`'s background-thread architecture (true); pre-fix verdict logic read `shingle_frac` alone (true — refutes the Contrarian's specific mechanism); zero test files/CI/pytest (true); "round 7 mutation testing" claim (false as stated — it's pass #3, different artifact); `SUSPECT`/`CONTAMINATED` constants still live (true); no noise-floor tool exists yet (true).

---

## 4. Chairman synthesis

See `COUNCIL RESPONSE §32` in `instructions.txt` (2026-07-26 ~22:50) for the full ranked critique, evidence-read list, leftover risks, "the questions themselves," and the one recommended next prompt. Summary in `council-report-2026-07-26_2250.md`.

---

*Watcher still armed on the DIRECTIVE block (task `bkk3n3jtj`) — fires on the next real DIRECTIVE rewrite.*
