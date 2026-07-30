# Council Report — srlm-forge — THE PHD, SOLO SEAT — activation #17

**Session:** 2026-07-30 ~03:57 — answer to the activation #17 DIRECTIVE at the top of
`instructions.txt`. Banked in the channel as **§75**, verbatim; this file is the
standalone artifact of the same text.
**Read scope:** `instructions.txt` §71–§74 (lines 8140–8546) plus code at commit
`eddb120` via `git show`, never the working tree.
**Trigger:** standing rule — always spawn the real PhD sub-agent for a channel update.
**Verdict:** GO-WITH-FIXES — four fix classes, one of which (instrument definition)
is free today and never again.

## Key numbers

- **Section 73's "INDEPENDENCE HOLDS, 1.01x" is measured against a null its own
  artifact disproves.** The greedy-corrected independence prediction is 0.0326, not
  0.0376, and the observed 0.0381 is **1.169x** it, CI [0.957, 1.500]. Two real
  effects cancel: −11% from the constant greedy draw, +14% from positive inter-task
  correlation (rho_bar = +0.0102 at T=31). The sizing table survives; its stated
  justification does not.
- **`ruler_set_sha256` has zero readers.** `git grep` over `eddb120` finds it written
  at `build_ruler.py:293` and read nowhere; `ruler_noise.ruler_tasks()` rebuilds the
  ruler from two unpinned files and never consults `data/ruler_frozen.json`.
- **pass@3 is a dead metric on this ruler and is still reported.** The greedy anchor
  imposes a hard floor of 0.600 on the 22/31 tasks whose greedy is pinned at 1.00, and
  E[pass@3] = 0.868 at the ruler's own mean rate — outside the band the ruler exists to
  enforce. The entire noise-floor/MDE apparatus is pass@1 only.
- **Claim A is false when `.venv-train` is absent** — `dataset_gate.verify_py()` falls
  back to `sys.executable` — and 4 of the 5 tests in `test_verifier_pin.py` report as
  passes in exactly that state.
- **Effective MDE for a live-channel effect is 3.5pp, not 3.0pp** (13% dilution from 4
  out-of-band channels).
- **Miller, "Adding Error Bars to Evals" (arXiv:2411.00640)** is new to the ledger and
  settles Q2: the planning formula carries per-arm variances `sigma_A^2/K_A +
  sigma_B^2/K_B`, and its `omega^2` term is the `tau^2/T` correction §59 named without
  a citation.

---

Per protocol, banked verbatim, not summarized. Full text as reported by the
seat follows. Read scope honoured at commit eddb120 via `git show`, never the
working tree; the working tree is on branch fix/screen-sizing-single-source and
was NOT read for any claim below.

Before the verdict, one sentence on what this round is: the instrument is in
better shape than any previous round's, and the two questions that decide the
next run are both answerable, but the headline claim of section 73 ("INDEPENDENCE
HOLDS, 1.01x") is comparing the measurement against a null its own artifact
proves wrong, three lines above the number that was banked. That is finding 1,
and it is the executor's own invited catch.

VERDICT: GO-WITH-FIXES.
  Fix classes, named: (A) INSTRUMENT DEFINITION, which must land BEFORE the first
  efficacy run because it is free now and never again; (B) ENFORCEMENT — the
  freeze is a receipt with no gate; (C) CLAIM HYGIENE — three stated conclusions
  do not follow from the numbers behind them; (D) ZERO-COST DESIGN — four changes
  that cost no generations and that the DIRECTIVE did not ask about, one of which
  (training-seed variance) is a larger unpriced variance component than the
  arm-heteroscedasticity Q2 is about. No NO-GO: nothing found invalidates the
  ruler, the pin, or the 40 replicates.

--------------------------------------------------------------------------------
EVIDENCE READ
--------------------------------------------------------------------------------
Channel, read directly (not from the DIRECTIVE's summary):
  instructions.txt lines 8140-8546 — sections 71, 72, 73, 74 in full, plus the
  tail of 70. instructions.txt lines 6672-6676 and 5004 for the section-header
  convention. Line 8507/8510 measured for separator width (80 dashes) and the
  file's line endings checked (8546 CRLF, 8546 LF -> uniformly CRLF).

Code at commit eddb120 (`git show eddb120:<path>`, verified the commit resolves
to "Section 74 + activation #17: bound the verifier damage, then arm the
council"):
  eval.py             all 293 lines
  forge.py            lines 35-50 (imports), 83-137 (the pin block +
                      verifier_interpreter), 430-514 (verify())
  dataset_gate.py     all 245 lines
  ruler_noise.py      lines 1-80 (docstring), 146-205 (ruler_tasks, cmd_measure),
                      233-296 (decompose), plus a symbol grep over the whole file
  build_ruler.py      lines 1-40 (docstring), 156-251 (cmd_freeze)
  screen_tasks.py     all 317 lines
  tests/test_verifier_pin.py   all 147 lines
  tests/test_ruler_noise.py    line count + the decompose contract as documented
                               in ruler_noise.decompose's docstring; I did NOT
                               read its seven scenarios line by line — labelled
                               so, see LEFTOVER RISKS.
  council/ruler_noise_analysis_n40.txt   all of it, at the pin
  OPEN-ITEMS.md       lines 1-75
  measure.py          lines 1-90
  git grep over eddb120 for: eval_history, ruler_frozen, ruler_set_sha256,
  set_sha256, 74560a4c, pass@3, KS
  data/ruler_frozen.json: NOT opened. The DIRECTIVE names it in scope and I read
  its producer (cmd_freeze) and its stated contents instead. Labelled.

Web sources FETCHED THIS ROUND (primary, this session):
  https://ar5iv.labs.arxiv.org/html/2107.03374 — Chen et al. 2021, Codex/
    HumanEval. Section 2.1 estimator + the temperature discussion.
  https://raw.githubusercontent.com/openai/human-eval/master/human_eval/
    evaluation.py — the official estimate_pass_at_k source.
  https://raw.githubusercontent.com/openai/human-eval/master/README.md — checked
    for a documented sampling protocol; it has none beyond num_samples=200.
  https://arxiv.org/html/2411.00640v1 — Miller, "Adding Error Bars to Evals".
    The five recommendations, the clustered-SE formula, the paired-difference
    formula, and the power formula. This is the decisive Q2 source and it is NEW
    to this project's ledger.
  https://arxiv.org/abs/2501.18101 — Diverse Preference Optimization (DivPO),
    abstract, for the sharpening/diversity-reduction sentence.
  https://arxiv.org/abs/2310.06452 — Kirk et al., "Understanding the Effects of
    RLHF on LLM Generalisation and Diversity", abstract.
  https://raw.githubusercontent.com/bigcode-project/bigcode-evaluation-harness/
    main/README.md — the canonical open code-eval harness's generation flags.
  https://pubmed.ncbi.nlm.nih.gov/10750058/ — Kieser & Friede, Stat Med 2000,
    internal-pilot variance re-estimation and type I error.
  Search passes that returned NOTHING usable and are reported as negative
  results, not silence: four searches for a primary source discussing a
  greedy/temperature-0 draw mixed into the n samples of an unbiased pass@k
  estimate; one for EvalPlus's stated decoding protocol (arXiv:2305.01210
  abstract does not state it). See Q1.

CARRIED from council/phd-research-log.txt, NOT re-fetched (not used for any new
claim except where marked): Chen et al. 2021 was re-fetched because Q1 makes a
NEW claim about it. Yue et al. 2504.13837 is used for a new claim (sharpening
direction) but only to the extent of its already-verified abstract; flagged
CARRIED-USED-FOR-NEW-CLAIM in the ledger. CodeDPO 2410.05605, DSTC 2411.13611,
Song 2406.01462, Tajwar 2404.14367, Xu 2404.10719, Pan 2508.18312, Wang
2504.20571, Chung 2210.11416, Ivison 2406.09279: not re-opened, not relied on.

EXECUTED this session (arithmetic only — no training, no generation, no
screening, no GPU, nothing that touches project state):
  One throwaway python script in the session scratchpad, over the 40 per-run
  pass@1 values printed in council/ruler_noise_analysis_n40.txt: batch split,
  Welch, OLS trend, ratio confidence intervals, the SIZING/MDE arithmetic, and
  the exact E[pass@3] / sd[pass@3] table for n=5. Numbers quoted below are from
  that run.

--------------------------------------------------------------------------------
FINDINGS — most decisive first
--------------------------------------------------------------------------------

F1. "INDEPENDENCE HOLDS ... 1.01x" is measured against a null the same artifact
    disproves. The correctly specified ratio is 1.17x, and the agreement at
    1.01x is two real effects cancelling.
    EXECUTED (arithmetic) + READ-ONLY (artifact).
    Target: instructions.txt:8438-8441 ("The independence prediction of 0.0376
    that section 70 derived is right to within 1%"), the DIRECTIVE's own
    "against the independence prediction 0.0376 - 1.01x, so INDEPENDENCE HOLDS",
    and screen_tasks.py:105-108 ("INDEPENDENCE HOLDS: observed/predicted is
    1.01x ... The sizing rows above are therefore CORRECT AS PUBLISHED").
    What breaks: council/ruler_noise_analysis_n40.txt prints, in this order,
      from confirmed rates (section 70's own input)  0.0376   ratio 1.01x
      from these runs' own mean rates               0.0365   ratio 1.04x
      same, minus the constant greedy draw          0.0326   ratio 1.17x
      CAUSE 1 ... tasks whose temp-0 draw was NOT constant across 40 runs: 0/31
    The 0.0376 prediction assumes five varying draws per task. The artifact
    proves on the line below that one of the five does not vary, on 31 of 31
    tasks, at n=40. The independence prediction that is actually consistent with
    the instrument is therefore 0.0326 (or 0.0333 from observed marginals), and
    the observed 0.0381 is 1.169x it — CI [0.957, 1.500], computed from the sd's
    own chi-square interval. Independence is not established as holding; what is
    measured is that a ~11% deflation from the greedy constant and a ~14%
    inflation from POSITIVE inter-task correlation cancel to within 1%. The
    artifact even prints the second one: "mean pairwise correlation +0.0102
    (reinforcement)". With T=31, Var(run mean) scales as (1 + rho_bar*(T-1)) =
    1 + 0.0102*30 = 1.306, i.e. sd x1.143 — which is exactly the gap between
    0.0333 and 0.0381. The decomposition is internally coherent; the CONCLUSION
    drawn from it is not.
    How bad: the sizing table survives untouched, because every MDE row is
    computed from the OBSERVED sd (0.0381), not from the prediction. So this is
    not a numbers error and no generation budget changes. It is worse than a
    numbers error in one specific way: the cancelling +0.0102 correlation is the
    single most load-bearing quantity for Q2, and calling the situation
    "independence holds" is what allows it to be forgotten. See Q2.
    And this is the executor's own invited catch, exactly as specified in the
    method note: section 73 corrected section 72 for banking a point estimate
    without its interval, and in the same breath banked "+0.0102 reinforcement"
    as a fact. Its interval spans both signs — the sd ratio CI against the
    greedy-corrected null is [0.957, 1.500], which contains 1.0, so zero
    covariance is not excluded at n=40 either. The sign flipped once already
    between n=10 and n=40; nothing yet establishes it a second time.

F2. THE FREEZE IS A RECEIPT WITH NO GATE. Nothing in the codebase reads
    ruler_set_sha256, and the only path that builds the 31 tasks does not read
    data/ruler_frozen.json at all.
    EXECUTED (git grep over eddb120).
    Target: build_ruler.py:293 writes "ruler_set_sha256": set_sha. `git grep -n
    "set_sha256\|ruler_sha\|74560a4c\|set_hash" eddb120 -- "*.py"` returns three
    hits, all inside build_ruler.py itself (lines 102, 293, 307). Zero readers.
    Meanwhile ruler_noise.py:146-172 ruler_tasks() rebuilds the ruler from
    data/ruler_confirmed.json + data/screen_results.jsonl and never consults the
    frozen artifact or its hash.
    What breaks: section 72's stated purpose for the freeze — "IT PINS THE TASKS,
    NOT THE TIDS. A tid is a pointer; if the payload can change, nothing is
    frozen" — is not enforced by any mechanism. data/screen_results.jsonl is an
    append-resumable log by design (screen_tasks.py:243-253) and
    data/ruler_confirmed.json is unpinned. The efficacy run will score whatever
    those two files say at the time, and no check compares the result to
    74560a4c. This is precisely the failure dataset_gate.py exists to prevent,
    one level up, and dataset_gate.py:159-174 already contains the correct
    pattern with the right name on it: "Parse, don't validate ... make the
    checked thing the only way to obtain what you need." The ruler has the
    receipt and skipped the require_verified.
    How bad: high for the integrity of any efficacy claim, low probability of
    firing by accident today, and the fix is ~15 lines. It is the second time
    this exact class has appeared in this project (receipt written, receipt not
    demanded) — by the standing rule, that means close the class, not the
    instance: any artifact that claims to pin something needs a loader that
    refuses to proceed without it.

F3. pass@3 IS A DEAD METRIC ON THIS RULER, IT IS STILL A REPORTED AGGREGATE, AND
    NO PART OF THE SIZING APPARATUS COVERS IT.
    EXECUTED (arithmetic) + READ-ONLY (code).
    Target: eval.py:39 `KS = (1, 3)`; eval.py:249-254 which computes and reports
    both; measure.py:57-62 which reads pass@3 out of the aggregate; against
    ruler_noise.py:255 `vals.append(p["correct"] / p["n"] ...)` — the entire
    noise floor, decomposition, MDE table and SIZING block are computed on the
    raw mean rate, which is pass@1 and only pass@1.
    What breaks, in two independent ways:
    (a) SATURATION. The admission band [0.2, 0.8] is defined on the per-sample
        temp-0.8 rate p. For n=5, E[pass@3] as a function of p is:
          p     0.20   0.30   0.40   0.49   0.60   0.70   0.80
          E     0.488  0.657  0.784  0.868  0.936  0.973  0.992
        At the ruler's own measured mean temp-0.8 rate (0.4905), pass@3 is 0.868
        — OUTSIDE the band the ruler was constructed to guarantee. A task at
        p=0.783 (ace_oss_16070's confirmed rate) reads 0.99 under pass@3: a dead
        channel. The band selection that section 64 through 70 spent three days
        and 343 screened candidates buying is undone by the choice of k.
    (b) THE GREEDY ANCHOR IMPOSES A HARD FLOOR, not just a bias. If the greedy
        draw passes, then c >= 1 by construction, so n-c <= 4 and pass@3 >=
        1 - C(4,3)/C(5,3) = 0.600 WITH PROBABILITY ONE. Greedy is pinned at 1.00
        on 22 of 31 tasks across all 40 runs. So on 71% of the ruler, reported
        pass@3 cannot go below 0.6 no matter what the model does. That is a
        stronger and more damaging statement than the pass@1 identity the
        executor found, and it appears nowhere in sections 71-74, in OPEN-ITEMS,
        or in the DIRECTIVE.
    How bad: decisive if any efficacy decision reads pass@3, harmless if none
    does — and nothing on record says which endpoint is primary, because no
    prereg exists (OPEN-ITEMS.md, "No Track A prereg"). Until one exists, both
    are live and the project is exposed to picking the flattering one after the
    fact. Cheapest fix: KS = (1,) plus a preregistered primary endpoint. If
    pass@3 is wanted for the Yue et al. narrowing question, it needs its own
    n (>= 10 draws per task, all at one temperature) and its own noise floor.

F4. CLAIM A IS FALSE IN ONE UNENUMERATED CONFIGURATION, AND THE TEST SUITE
    REPORTS GREEN IN EXACTLY THAT CONFIGURATION.
    READ-ONLY.
    Target: dataset_gate.py:91-98 —
        def verify_py() -> str:
            env = os.environ.get("SRLM_VERIFY_PY")
            if env: return env
            if _VENV_PY.exists(): return str(_VENV_PY)
            return sys.executable
    and tests/test_verifier_pin.py:73-74, 84-86, 102-104, each of which is
        if not VENV_PY.exists():
            print("    (skipped: ...)"); return
    What breaks: Claim A says the verdict "can no longer depend on which script
    called it, because the interpreter is resolved in one place and no longer
    inherited from sys.executable." If .venv-train\Scripts\python.exe is absent
    — fresh clone, venv rebuilt under a different name, venv relocated, a
    teardown mid-experiment — verify_py() returns sys.executable and the ORIGINAL
    DEFECT IS BACK, silently, with no warning and no error. The resolution is
    still in one place; the INHERITANCE is not removed, it is one missing
    directory away. And in that same state, four of the five tests in
    test_verifier_pin.py return early and are counted as passes by the file's own
    __main__ runner (lines 137-146 only catch AssertionError; an early return is
    a pass). So "tests/test_verifier_pin.py 5/5" is evidence that .venv-train
    exists on this machine today, not evidence that the pin holds. The one test
    that does run unconditionally, test_env_override_is_honoured, asserts the
    override works — it does not assert the fallback is safe.
    The DIRECTIVE's own scope caveat names the right unknowns (other 3.11<->3.14
    semantics, packages, OS, CPU) and does not name this one, which is not an
    unknown at all: it is readable in eight lines of the module that holds the
    pin.
    How bad: moderate-to-high, because the failure is silent and the guard is
    blind at exactly the moment it matters. Two-line fix (raise, or record
    "UNPINNED" in the fingerprint and make the gate refuse it) plus turning the
    skips into explicit skip-reporting that does not read as a pass.

F5. THE PIN IS BOUND AT IMPORT TIME, AND SECTION 74'S MEASUREMENT IS ONLY VALID
    IF EACH ARM WAS A SEPARATE PROCESS. The channel does not say.
    READ-ONLY. This is a question, not an accusation.
    Target: forge.py:126 `VERIFY_PY = dataset_gate.verify_py()` — a module-level
    constant, read by verify() at forge.py:493. And dataset_gate.py:88,107-119 —
    interpreter_fingerprint() memoises into the module global _INTERP_CACHE on
    first call.
    What breaks: section 74 says "100 completions ... replayed through verify()
    with the verifier forced to each interpreter in turn (SRLM_VERIFY_PY,
    emulating the pre-pin inherit)". If that was done by mutating os.environ
    between the two passes inside ONE process that had already imported forge,
    then VERIFY_PY never changed, both passes ran the same interpreter, and
    "87/100 both, per-task counts IDENTICAL on all 10 tasks, zero disagreements"
    is the same measurement twice — a tautology, and section 74's conclusion
    ("the pre-pin eval_history rows for the old bank are NOT affected") would be
    unsupported. If each arm was a fresh subprocess with the env var set before
    launch (which is how tests/test_verifier_pin.py correctly does it, lines
    119-123), section 74 stands as written. I cannot tell from the channel, and
    the replay script is not named in section 74 or in the read scope.
    How bad: potentially fatal to section 74 specifically, zero effect on
    sections 71-73 (whose red witness used two real launchers, which cannot have
    this bug). Resolvable in one minute by quoting the launch command. This is
    also a durable trap: the same shape will bite the next person who tries to
    re-pin in-process, and a one-line assert in the replay harness
    (`assert forge.VERIFY_PY == expected`) closes it permanently.

F6. THE REPORTED pass@1 IS BIASED +2.45pp AGAINST THE POLICY IT CLAIMS TO
    SAMPLE, THE BIAS IS 81% OF THE MDE, AND IT DOES NOT SAFELY CANCEL.
    EXECUTED (arithmetic).
    Target: eval.py:223-224 and the artifact's own line "eval-instrument rate
    minus confirmed: mean +0.0247".
    What breaks: reported = 0.2*greedy + 0.8*p. Measured, mean greedy 0.6129 and
    mean temp-0.8 0.4905, so 0.2*(0.6129-0.4905) = +0.0245 — the artifact prints
    +0.0247 and the residual is rounding. The instrument reads 0.5150 where the
    temp-0.8 policy's pass@1 is 0.4905. That is 81% of the 3.02pp MDE, carried as
    a constant. A constant cancels in a difference ONLY IF (greedy - p) is
    invariant under training, and the sharpening literature predicts specifically
    that it is not: DivPO (arXiv:2501.18101, verbatim) "Post-training of language
    models, either through reinforcement learning, preference optimization or
    supervised finetuning, tends to sharpen the output probability distribution
    and reduce the diversity of generated responses." Sharpening moves the
    temp-0.8 distribution toward the greedy mode, so p rises toward greedy, the
    gap closes, and the reported rate rises — with the model having acquired
    nothing new, in exactly the sense Yue et al. (2504.13837, CARRIED) describe.
    How bad: this is the mechanism most likely to produce a FALSE POSITIVE on the
    first efficacy run, and it is also the cheapest thing in this whole review to
    defend against, because eval.py ALREADY STORES the discriminator: per-task
    `greedy` and `sampled` are both persisted (eval.py:238-240). Greedy flat and
    p rising = sharpening. Both rising = capability. That diagnostic is worth
    more than the 0.894x variance reduction the anchor was kept for, which
    reframes Q1 — see the answer.

F7. screen_tasks.py's computed banner prints a false direction word, and both
    branches assume the observed sd is BELOW the prediction.
    EXECUTED (evaluated the branch by hand: 0.0312 <= 0.0376 <= 0.0489 -> True).
    Target: screen_tasks.py:300-311. `ratio` and `contains` are computed;
    the printed claim is hardcoded per branch:
      contains  -> "so the shortfall is a DIRECTION, not an established fact -
                    the rows above are not yet safe to tighten."
      else      -> "excludes the assumed value, so the rows above are
                    conservative."
    What breaks: at the current NOISE_FLOOR values the ratio is 1.013 — an
    EXCESS, not a shortfall — and the banner says "shortfall" anyway. If the CI
    ever tightens to exclude the prediction from ABOVE, the else-branch will
    announce that the rows are "conservative" when they are the opposite. Section
    72 credited this refactor with closing the class ("the banner COMPUTES its
    caveat rather than carrying a second copy of the status"). It computes the
    NUMBER and hardcodes the CLAIM, which is the same class one layer in.
    How bad: low operationally, high as a pattern — this is the third instance of
    "the stale thing is the sentence, not the figure" in this file's history
    (sections 65, 67, 72). Fix: derive the direction word from the ratio, and
    make the tests assert the sentence for both signs.

F8. THE "3pp = k=25 = 3,875 gens/arm" PRICE IS NOT WHAT screen_tasks.SIZING
    SAYS, AND SIZING'S INPUT WAS NEVER RE-DERIVED FROM THE FROZEN RULER.
    EXECUTED (arithmetic).
    Target: screen_tasks.py:88-92 `SIZING = {3.0: 3889, 5.0: 1400}` against
    instructions.txt:8448-8450, the DIRECTIVE's "3pp = k=25 = 3,875
    generations/arm", and OPEN-ITEMS.md's identical claim.
    What breaks, two small things that compound:
    (a) 3,875 = 31*5*25 is 14 generations SHORT of the file's own 3889. At T=31
        and N_SAMPLES=5, SIZING[3.0] requires ceil(3889/155) = 26 runs = 4,030
        generations. And the MDE actually implied by sd=0.0381 at k=25 is
        2.8016*0.0381*sqrt(2/25) = 3.019pp, quoted as "3.0pp" in three places.
        Neither matters for a decision; both are quoted as exact.
    (b) SIZING's 3889 comes from mean p(1-p) = 0.2230, and screen_tasks.py:69-72
        states its provenance honestly: "re-derived from the 30 admitted PILOT
        tasks". The frozen 31-task ruler's implied value is 0.2190
        (ruler_noise.py's selftest asserts exactly that literal against section
        70's table). The sizing constant governing the next run was derived from
        a task set that has been REPLACED, and it agrees with the replacement to
        within 2% by coincidence. Nothing is wrong with the number; the RECORD is
        wrong about where it came from.
    How bad: low. Named because the project's own rule is that a quoted figure
    must be traceable to a live derivation, and this one is traceable to a dead
    one.

F9. EFFECT DILUTION FROM THE 4 OUT-OF-BAND TASKS IS ~13%, WHICH IS BIGGER THAN
    EVERY SIZING ADJUSTMENT ARGUED ABOUT IN SECTIONS 70-73. This also answers the
    DIRECTIVE's own omission candidate about degrees of freedom, in the negative.
    EXECUTED (arithmetic).
    Target: the DIRECTIVE's omission candidate "whether the 4 flagged
    out-of-band tasks should affect degrees of freedom in the MDE calculation",
    and instructions.txt:8478-8487.
    Finding: degrees of freedom is the wrong axis. The estimator is a mean over
    31 FIXED tasks; the tasks are not a sample, so they contribute no df to
    anything, and their low variance is already inside the measured 0.0381
    (ruler_noise.decompose sums OBSERVED per-task variances, ruler_noise.py:266).
    The cost is not validity, it is SIGNAL. ace_oss_16070 at 0.880 and
    ace_oss_24748 at 0.145 are declared by the executor to carry "almost no
    signal". If 4 of 31 channels cannot move, a true effect of delta on the live
    channels reads as (27/31)*delta = 0.871*delta on the 31-task mean. The
    honest MDE for a live-channel effect at k=25 is therefore 3.019/0.871 =
    3.47pp, not 3.0pp. That 0.45pp of dilution is larger than the entire
    difference between section 72's withdrawn table and section 73's restored
    one.
    How bad: moderate, and the right response is NOT to drop the four (the
    executor's reasoning about selecting on the reported measurement is correct
    and I endorse it). The right response is to pre-register BOTH estimands: the
    31-task mean (the frozen, unbiased-by-selection number) and the 27-live-task
    mean (the sensitivity analysis), declare the 31-task one primary, and quote
    3.5pp as the effective sensitivity rather than 3.0pp.

F10. THE BATCH-DRIFT ALTERNATIVE TO SECTION 73'S CORRECTION: I TESTED IT AND IT
     FAILED. Reported because section 73 asserted a cause without testing the
     competing one, and section 71's own method note is "check the SIGN your
     explanation predicts, before believing it."
     EXECUTED.
     Section 73 attributes the entire n=10 -> n=40 change (sd 0.0283 -> 0.0381,
     covariance sign flip) to small-sample noise. The 40 replicates are two
     batches run at different times (10 from section 72, 30 from section 73), so
     drift or a changed server state is a live alternative that would produce the
     same signature. Over the 40 per-run values printed in
     council/ruler_noise_analysis_n40.txt:
       batch 1 (runs 1-10)   mean 0.5168   sd 0.0283
       batch 2 (runs 11-40)  mean 0.5144   sd 0.0412
       F(29,9) = 2.13                     (not significant at alpha=.05)
       Welch on the two means: t = 0.203, df = 22.7
       OLS trend on run index: -0.00032 per run, t = -0.61,
         corr(run index, run mean) = -0.0986
     No detectable drift in level or in spread. Section 73's attribution
     survives a test section 73 did not run. This is a null finding in the
     executor's favour and I am recording it as one.

F11. A CITED LINE RANGE IS WRONG. READ-ONLY.
     The DIRECTIVE says "eval.py:211-213 does not feed it that. It takes sample 0
     at temp 0.0 and the remaining 4 at temp 0.8." At eddb120, eval.py:211-213 is
     comment prose ("...therefore over-predicts, for a reason that has nothing to
     do with the / per-task independence the prediction is usually blamed on. /
     Keeping `greedy`"). The mixture itself is eval.py:223-224:
         for i in range(N_SAMPLES):
             temp = 0.0 if i == 0 else TEMP  # one greedy anchor + diverse rest
     eval.py:164 pass_at_k is correct as cited, and its body at 166-168 matches
     openai/human-eval's estimator exactly including the n-c<k early return.
     How bad: trivial in itself. Named because section 61 established the rule
     that every cited symbol is checked to exist before the DIRECTIVE is written,
     and the DIRECTIVE asserts that rule was followed ("Every symbol cited below
     was checked to exist at that commit"). A symbol was; a line range was not.
     The rule should cover both or should say it only covers symbols.

F12. measure.py:63 COMPUTES A POPULATION SD ON THREE RUNS. READ-ONLY, low.
     `std = (sum((x - mean) ** 2 for x in p1) / len(p1)) ** 0.5` divides by n,
     not n-1, so it understates the sd by a factor sqrt(2/3) = 0.816 at
     NOISE_RUNS=3. This is the legacy night-1 path on the OLD bank and is not in
     the current chain. I did NOT trace which channel figures descend from it, so
     this is a flag on the code, not a claim about any published number.

F13. MULTIPLICITY IS SMALL, REAL, AND UNPRICED — AND THE ONE PLACE THE DIRECTIVE
     SUSPECTED IT, IT IS CLEAN. READ-ONLY.
     The DIRECTIVE's omission candidate was "multiple-comparisons exposure from
     having asked 'is the CI's shortfall real' repeatedly across sections 71-73".
     Checked: not a violation. Section 72 pre-specified the top-up ("~40
     replicates would halve the interval ... That is the next measurement, not
     the next guess") and section 73 ran exactly that. A pre-specified sample
     size is not optional stopping. Credit given.
     Where multiplicity IS unpriced: two reported endpoints (KS=(1,3), F3), a
     held-in series and a held-out series, and 31 per-task readouts with no
     declared status. At two endpoints and alpha=.05 each, familywise error is
     ~9.8%. The fix is not a correction factor, it is a prereg naming one primary
     endpoint and labelling everything else descriptive.

--------------------------------------------------------------------------------
OMISSION ATTACK — what activation #17 did not name
--------------------------------------------------------------------------------

O1. TRAINING-SEED VARIANCE. This is the largest unpriced variance component in
    the entire sizing, it is larger than the arm-heteroscedasticity Q2 asks
    about, and no eval budget reduces it. Every MDE in sections 70-73 is
    conditional on TWO FIXED MODELS: the run-level sd measures generation
    sampling noise given a null model and (by assumption) given a trained model.
    One training run is one draw from the training process. With one adapter, a
    +3pp reading cannot be attributed to the intervention rather than to that
    particular adapter — and DPO at 918 pairs over 13 prompts is precisely the
    regime where the seed matters most, which is the executor's OWN recorded R5
    confound (rpo_alpha, Pan et al. + Xu et al. Theorem 4.1) pointing at the same
    thing from a different side. Increasing k from 5 to 25 buys precision on a
    quantity that is not the one in question.
    Cheapest response, and it is a REALLOCATION not an increase: the currently
    planned budget is 2 arms x 3,875 = 7,750 generations. Three trained seeds
    plus one null at k=12 is 4 x 31 x 5 x 12 = 7,440 generations — cheaper — and
    it answers "does seed variance exist" while still giving a 4.4pp
    per-arm sensitivity. If the three seeds disagree by more than 4pp, the k=25
    single-seed run was never going to mean anything and this discovers it for
    less money. Recommendation: do this BEFORE, or instead of, the k=25 run.

O2. ARM-ORDER CONFOUNDING. All 40 null replicates were collected in two blocks;
    the trained arm will be a different Ollama model tag, loaded separately, at a
    different time. Model load, resident quantization, num_ctx=2048 handling and
    server state are therefore perfectly confounded with arm. Nothing in sections
    71-74 mentions interleaving or run-order randomization. The fix is free:
    alternate arms run by run (A,B,A,B,...) inside one session and record the
    order. As it stands, if the trained arm reads +3pp, "the second block ran
    warmer" is not excludable, and section 73's own no-drift result (F10) is
    reassurance about ONE model in ONE session, not about a model swap.

O3. THE DATA-DEPENDENT DENOMINATOR. eval.py:250 `usable = [p for p in per_task
    if p["n"] >= k]` silently changes the estimand when a task loses samples to
    generation errors. Zero errors in 40 runs, so it has never fired — but a
    re-injected/adapted model is a plausible source of an ASYMMETRIC error rate,
    and then the two arms are means over different task sets. Free fix: refuse
    the run (or refuse the row) if any task has n < N_SAMPLES, rather than
    quietly dropping tasks from one arm's denominator.

O4. NO PREREG, WHICH MAKES EVERY POWER NUMBER A BUDGET RATHER THAN A TEST.
    OPEN-ITEMS.md records this ("No Track A prereg"), so it is not hidden — but
    the DIRECTIVE asks three sizing questions without noting that nothing yet
    commits to a primary endpoint, a direction, a decision rule, or an analysis.
    Q1's instrument change, F3's endpoint choice, F9's two estimands and F13's
    multiplicity all collapse into one cheap artifact: a signed prereg written
    BEFORE the first efficacy run. It costs an hour and it is the difference
    between a measurement and a story.

O5. IS THE GREEDY MIXTURE ONE PROBLEM OR TWO? The DIRECTIVE asks whether the
    binomial/independent-Bernoulli assumption is violated by the same mixture
    Q1 flags. Answer: it is ONE mechanism with TWO distinct consequences, and
    they need different fixes. (i) ESTIMATOR bias: the n=5 draws are not
    exchangeable, so pass_at_k's hypergeometric argument does not apply — this is
    fixed only by changing what is sampled. (ii) VARIANCE misspecification: one
    draw contributes zero variance, so any p(1-p)/N prediction over-predicts by
    exactly N/(N-1) in variance, i.e. 1.118x in sd — this is already correctly
    handled in ruler_noise.decompose (the `pred_greedy` term, eff_n = N^2/(N-1)),
    and it is the term section 73 then dropped from its conclusion (F1). So: one
    cause, two consequences, one of them already instrumented and then
    un-reported. Not two problems.

--------------------------------------------------------------------------------
ANSWERS TO Q1 / Q2 / Q3
--------------------------------------------------------------------------------

Q1 — IS THE GREEDY+SAMPLED MIXTURE FED TO THE UNBIASED ESTIMATOR DOCUMENTED
     PRACTICE, DOCUMENTED ERROR, OR UNADDRESSED? AND IS "pass@3" THE QUANTITY IT
     NAMES?

  ANSWER: UNADDRESSED. Not endorsed, not named as an error — the canonical
  sources do not contemplate it, and two of them are structurally incapable of
  producing it. Then: NO, pass@3 as this file reports it is not the quantity it
  names, and pass@1 is not either, though pass@1 is at least a well-defined and
  reproducible functional.

  The literature, primary sources fetched this round:
  - Chen et al. 2021 (arXiv:2107.03374, Section 2.1, fetched via ar5iv this
    session): "to evaluate pass@k, we generate n>=k samples per task (in this
    paper, we use n=200 and k<=100), count the number of correct samples c<=n
    which pass unit tests, and calculate the unbiased estimator" pass@k :=
    E[1 - C(n-c,k)/C(n,k)]. The paper TUNES ONE TEMPERATURE PER REPORTED k:
    "for a 679M parameter model, the optimal temperature for pass@1 is T*=0.2 and
    the optimal temperature for pass@100 is T*=0.8", and "Using the optimal
    temperatures 0.2 and 0.8 for pass@1 and pass@100, we plot these two metrics
    as a function of model size." Two metrics, two separate sampling runs, one
    temperature each. Greedy/temperature-0 appears nowhere in the pass@k
    sections; the lowest temperature discussed is 0.2. Notably, the paper does
    NOT explicitly state an IID requirement — the requirement is implicit in the
    derivation, which counts k-subsets of n exchangeable draws.
  - openai/human-eval, human_eval/evaluation.py (fetched this session):
    estimate_pass_at_k takes only (num_samples, num_correct, k). It has no
    knowledge of how the samples were produced and therefore cannot detect or
    correct a mixture. The repo README documents num_samples_per_task = 200 and
    states no temperature protocol at all.
  - bigcode-evaluation-harness README (fetched this session): the generation
    interface is a single `--temperature` plus a single `--do_sample` plus
    `--n_samples`. There is no way to express "one greedy draw and four at 0.8"
    within one n_samples set. The canonical open harness cannot produce srlm-
    forge's instrument. That is the strongest available evidence that the mixture
    is outside documented practice: not that someone warned against it, but that
    the reference implementations have no API for it.
  - Four targeted searches for a paper analysing a greedy draw mixed into an
    unbiased pass@k estimate returned nothing primary. What search returns is
    LLM-written glosses asserting the violation; I am refusing those as evidence
    and reporting the absence instead, per section 62's precedent with
    arXiv:2603.20100. So: the literature does not address this. Nobody has
    written it down. That is the citation you asked for, in the negative, and it
    means the argument has to be made arithmetically — which is fine, because it
    is arithmetic.

  WHAT THE INSTRUMENT ACTUALLY REPORTS. With one deterministic draw g in {0,1}
  and four IID Bernoulli(p):
  - k=1: E[reported] = 0.2g + 0.8p exactly. This is the identity section 71's H1
    found, and it is a tautology of the arithmetic, not a discovered effect. It
    is a legitimate, reproducible, monotone functional of the model — but it is
    the pass@1 of NO sampling policy, and on this ruler it sits +2.45pp above the
    temp-0.8 policy's pass@1 (F6).
  - k=3: worse, and qualitatively different. The estimator is nonlinear in c, so
    there is no mixture-weight interpretation at all. Concretely: g=1 forces
    c>=1, hence reported pass@3 >= 1 - C(4,3)/C(5,3) = 0.600 with probability 1
    — a floor imposed by a deterministic draw, on the 22/31 tasks where greedy is
    pinned high. Where g=0, four varying draws plus one guaranteed failure give a
    downward-biased estimate of the temp-0.8 pass@3. Layer that on the saturation
    arithmetic in F3 (E[pass@3] = 0.868 at the ruler's own mean rate) and pass@3
    on this instrument has a usable range of roughly [0.6, 1.0] on most tasks.
    "pass@3" is not the quantity it names, twice over.

  WHAT YOU LOSE BY DROPPING THE GREEDY DRAW — priced, not argued:
  - You lose the 1.118x sd reduction, exactly as measured. Five IID draws at 0.8
    gives per-task variance p(1-p)/5 against the current 4p(1-p)/25, a ratio of
    1.25 in variance and 1.118 in sd: 0.0381 -> 0.0426. Holding the MDE at
    3.019pp then needs k = 25 * 1.25 = 31.25 -> k=32, i.e. 4,960 generations per
    arm instead of 3,875. +1,085 generations, about +15 minutes per arm at the
    measured 2.1 min/replicate. That is the whole cost.
  - You lose the SHARPENING DIAGNOSTIC, and this is the part the DIRECTIVE has
    not priced. It is worth more than the variance reduction (F6). So do not drop
    the greedy draw — UNSCORE it. Three options, priced:
      (A) 5 IID at temp 0.8, greedy gone.        sd 0.0426, k=32, 4,960 gens/arm.
          Clean estimator. Diagnostic lost.
      (B) 4 IID at 0.8 scored, 1 greedy recorded but excluded from n.
          Per-task variance p(1-p)/4 -> sd 0.0476, k=39, 6,045 gens/arm.
          Clean estimator, diagnostic kept, most expensive.
      (C) 6 draws: 1 greedy recorded-and-unscored + 5 IID at 0.8.
          sd 0.0426, k=32, 5,952 gens/arm. Clean estimator AND diagnostic, at
          +20% over (A) and +54% over today's price.
    RECOMMENDATION: (C). It loses nothing the literature or the arithmetic
    identifies, and the +2,077 generations against today's plan is ~30 minutes of
    GPU time at the measured 75 generations/minute, against a defect that is 81%
    of your MDE.
  - THE SCHEDULING ARGUMENT, which I think is the decisive one and which the
    DIRECTIVE has backwards. "Changing it re-baselines every eval_history.jsonl
    row" is true of the OLD 10-task bank, which is already retired by section 64
    and is a different task set. On the NEW ruler the entire corpus is 40 null
    replicates costing 2.1 minutes each. Re-measuring the null arm under a new
    protocol is ~85 minutes at option (A) and ~100 at (C). One evening, today.
    The moment a trained arm exists, that cost doubles and becomes
    non-recoverable, because the trained artifact's replicates cannot be re-run
    against a changed instrument without re-running the arm. Change it now or
    accept it permanently. There is no cheaper moment than this one.

Q2 — DOES THE LITERATURE REPORT PER-ARM VARIANCE ON pass@k OR ASSUME
     HOMOSCEDASTICITY? IS THERE A DOCUMENTED DIRECTION FOR A TRAINED ARM? WHAT IS
     THE CHEAPEST DESIGN WHEN ONLY ONE ARM CAN BE PRE-MEASURED?

  (a) THE METHODOLOGY LITERATURE PRESCRIBES PER-ARM VARIANCE. Your sqrt(2)*sd is
  the special case, not the standard. Miller, "Adding Error Bars to Evals"
  (arXiv:2411.00640, HTML fetched this session — NEW to this project's ledger and
  the single most relevant paper anyone has cited into this project on eval
  statistics) gives the planning formula as
      n = (z_{alpha/2} + z_beta)^2 * (omega^2 + sigma_A^2/K_A + sigma_B^2/K_B)
          / delta^2
  with omega^2 = Var(x_A) + Var(x_B) - 2*Cov(x_A, x_B), and sigma_A^2, sigma_B^2
  the two arms' EXPECTED CONDITIONAL VARIANCES with their own resampling counts
  K_A, K_B. Per-arm, explicitly, both in the variance and in the resampling
  count. se_diff = sqrt(2)*run_sd is what that formula collapses to when you
  substitute sigma_A = sigma_B and K_A = K_B; it is not a different school of
  thought, it is your formula with an assumption baked in.
  Two further things from the same paper that land directly on this project:
  - Its five recommendations are: CLT standard errors; clustered SEs when
    questions come in related groups; variance reduction by resampling answers
    and by analysing next-token probabilities; "When two models are being
    compared, conducting statistical inference on the question-level paired
    differences, rather than the population-level summary statistics"; and using
    power analysis to determine whether an eval can test the hypothesis at all.
  - omega^2 IS the tau^2/T term section 59 finding 2 named without a citation.
    You have been carrying the right correction with no source; this is the
    source. It also confirms the correct reading of your own estimand: because
    you explicitly do NOT claim generalisation, your 31 tasks are fixed rather
    than drawn, omega^2 = 0 for your declared estimand, and se_diff =
    sqrt(sd_A^2/k_A + sd_B^2/k_B) is then EXACTLY right. Your formula is correct
    for the claim you are making. Do not let me talk you into a paired-across-
    tasks variance reduction here — for a fixed-task estimand it buys nothing,
    because there is no between-task variance component in the estimand to
    remove. Pairing becomes mandatory the moment you want the generalisation
    claim, and then omega^2 enters and pairing removes the task-difficulty term.
  (b) THE EMPIRICAL preference-learning / RLVR code literature does NOT report
  per-arm pass@k variance. I looked and did not find it; the papers already in
  this project's ledger (CodeDPO Table 7, DSTC Tables 2-3, ACECODER, Ivison et
  al. Table 7 — all CARRIED, not re-opened) report point estimates per
  configuration. I am stating that as "searched, not found", not as "does not
  exist". The gap is real and it is why Miller's paper exists.
  (c) DIRECTION UNDER DPO — the documented direction is variance DOWN, and I
  believe the documented direction is the wrong one to plan against, because your
  own n=40 decomposition contains the counterweight and it is bigger.
    DOWN, cited: DivPO (arXiv:2501.18101, abstract fetched this session,
    verbatim) "Post-training of language models, either through reinforcement
    learning, preference optimization or supervised finetuning, tends to sharpen
    the output probability distribution and reduce the diversity of generated
    responses." Kirk et al. (arXiv:2310.06452, abstract fetched this session,
    verbatim) "RLHF significantly reduces output diversity compared to SFT across
    a variety of measures, implying a tradeoff in current LLM fine-tuning methods
    between generalisation and diversity." Yue et al. (2504.13837, CARRIED) is
    the same direction from the pass@k side. Mechanically: sharpening pushes
    per-task p toward 0 or 1, p(1-p) falls, per-task variance falls, run-level sd
    falls, and your MDE is conservative. So YES, the direction you hoped for is
    the documented one.
    UP, from your own data: the run-level sd is not just a sum of per-task
    variances, it is (1 + rho_bar*(T-1)) times it, and your n=40 artifact
    measures rho_bar = +0.0102, which at T=31 is already a 1.31x variance
    inflation (F1). Inter-task correlation is exactly what a SHARED training
    effect produces: a model that changes its import habits, its output format,
    or its annotation habit — the very habit section 71 found — moves many tasks
    together. Sensitivity: if per-task variance falls 20% from sharpening but
    rho_bar rises to 0.05, the variance factor goes 0.8 * (1+0.05*30) / 1.306 =
    1.53, i.e. sd UP 24% despite the sharpening. rho_bar = 0.10 gives sd up ~57%.
    Small changes in inter-task correlation dominate plausible changes in
    marginal variance at T=31. CONCLUSION: the sign is genuinely indeterminate
    and you may not treat the MDE as conservative. The DIRECTIVE's hopeful
    reading ("entropy collapse would REDUCE variance, which would make my MDE
    conservative") is half the picture and it is the smaller half.
  (d) THE CHEAPEST DESIGN THAT DOES NOT REQUIRE KNOWING THE TRAINED ARM'S sd IN
  ADVANCE. Four items, cheapest first, and the first two cost nothing:
    1. REPORT EACH ARM'S OWN sd FROM ITS OWN REPLICATES, and do the inference as
       WELCH, not pooled: se_diff = sqrt(sd_A^2/k_A + sd_B^2/k_B) with
       Welch-Satterthwaite df. At k_A = k_B = 25 the df is between 24 and 48, so
       nothing is lost to the approximation. This is Miller's formula written
       out, it needs no advance knowledge, and it converts the unmeasurable
       assumption into a measured quantity at analysis time. Cost: zero.
       Non-negotiable: your section 72/73 open item 1 already says "the first
       efficacy run must report its own arm sd rather than borrowing this one" —
       that instinct is correct, this is its formal name and its formula.
    2. PRE-COMMIT TO REPORTING THE CONFIDENCE INTERVAL OF THE DIFFERENCE AND THE
       ACHIEVED (post-hoc) SENSITIVITY, and treat the pre-run MDE as a BUDGET,
       not a promise. A CI requires no advance variance; only a power guarantee
       does. This single change makes the unmeasurable assumption a non-blocker:
       if the trained arm turns out noisy, the CI says so honestly and you have
       lost nothing but width. Cost: zero.
    3. IF YOU WANT A POWER GUARANTEE, USE AN INTERNAL PILOT, WITH THE ALPHA
       ADJUSTMENT — do not re-estimate the variance naively. Kieser & Friede,
       Statistics in Medicine 2000 (PubMed 10750058, abstract fetched this
       session): recalculating sample size from an interim variance estimate is a
       standard, accepted design, and "the type I error rate may be inflated by
       this procedure"; the paper's contribution is achieving strict alpha
       control via an adjusted critical value or a downweighted alpha level.
       Wittes & Brittain's original restriction (final n never below the planned
       n) is the simple safe form. Concretely for you: run k=10 in BOTH arms,
       re-estimate BOTH sds, top up to the k those sds require, and pre-commit
       the adjusted critical value before looking. This is the textbook answer to
       "I must size on a variance I can only measure after starting", and it is
       the answer to Q2's literal question.
    4. PAIRED-BY-TASK ANALYSIS: do it, but for the right reason. Not for variance
       reduction (see (a) — your estimand has no between-task component to
       remove) but because it is Miller's recommendation 4 for the diagnostic
       question and because it is the only analysis that supports the
       generalisation claim if you ever want it. Report per-task deltas as
       descriptive alongside the primary number.
    And ONE THING NOT TO DO: do not spend the whole budget on k in one arm pair
    before you know whether training-seed variance swamps it (O1).

Q3 — DOES R2 STILL HOLD AT 13? HAS THE INSTRUMENT SWAP ALREADY SPENT THE
     ONE-CHANGE-AT-A-TIME BUDGET R2 WAS PROTECTING?

  ANSWER: YES, the budget is spent, and worse than the DIRECTIVE frames it. R2 is
  VOID as written, not because holding at 13 became wrong, but because the run
  R2 was designed to be a controlled comparison FOR no longer has anything to be
  compared against.

  R2's purpose was that the seam fix and the prompt count not change together, so
  the seam-fix re-run would be readable against section 61's -0.8pp held-out
  result. That comparison is now impossible for three independent reasons, any
  one of which is sufficient:
  (i) The instrument changed. Section 61's -0.8pp was measured on the 10-task
      bank; the re-run would be measured on 31 band-selected AceCode oss tasks.
      Different tasks, different distribution, different verifier.
  (ii) The old instrument was incapable of the measurement anyway. Section 64:
      base pass@20 = pass@5 = pass@3 = 0.9000 exactly, 7 of 10 at ceiling. A
      -0.8pp reading on an instrument with 3pp of headroom and a ~2.6pp MDE was
      never evidence, which is your own conclusion and I agree with it.
  (iii) The verifier changed the definition of "correct" (section 71). Section 74
      shows the OLD bank's task shapes do not trip the KNOWN mechanism, which
      narrows the damage but does not restore comparability — and section 74's
      own validity is conditional on F5.
  So holding prompt count at 13 does not isolate the seam fix. Nothing isolates
  the seam fix any more; the seam fix is already isolated, by the section 71 red
  witness, which is a cleaner isolation than any training run could have given
  (310 replayed completions, zero generation noise). The seam-fix re-run has no
  remaining job.

  WHAT THE NEXT RUN IS ACTUALLY A MEASUREMENT OF, stated plainly so it is not
  mislabelled in the channel: it is a FIRST BASELINE PLUS A FIRST EFFICACY POINT
  on a new instrument, answering an existence question — "does 13-prompt,
  918-pair, off-policy, rpo_alpha=1.0 DPO move a live 31-task band-selected ruler
  by more than the ruler can resolve?" It is not a controlled re-run of anything.
  It cannot attribute an effect to the seam fix, to the prompt count, to
  rpo_alpha, or to the seed, because all four differ from every prior run and
  three of them have never been varied deliberately.

  THEREFORE R2 SHOULD BE REPLACED, NOT PRESERVED — and this changes my
  predecessor's ruling, which I am flagging as a change rather than sliding it
  in. The one-variable-at-a-time discipline is still right; it now applies to a
  different variable. The variable worth freezing is THE INSTRUMENT, not the
  prompt count. Which inverts the ordering the DIRECTIVE assumes:
    R6 (supersedes R2). Change the eval sampling protocol NOW, per Q1 option (C),
       re-measure the null arm's noise floor under it (~100 min), and then FREEZE
       eval.py's sampling protocol for the whole prompt-count sequence. Prompt
       count may then move freely, because it is no longer entangled with an
       instrument change. Holding prompt count at 13 for its own sake buys
       nothing now.
    R7. Before or instead of a k=25 single-seed run, spend the same generations
       on 3 trained seeds + 1 null at k=12 (O1). Cheaper, and it measures the
       variance component that no amount of k can reduce.
  Does Q3 change my Q1/Q2 answers? Yes, in one direction each. It makes the Q1
  change URGENT rather than optional — it is free today, non-recoverable
  tomorrow, and there is no baseline left to protect by delaying. And it makes
  Q2's "report each arm's own sd" MANDATORY rather than good practice, because
  there is now no historical arm from which any sd could be borrowed even in
  principle.

--------------------------------------------------------------------------------
THE CLOSED-CLASS CLAIM AND THE SIX NON-CLAIMS, ATTACKED
--------------------------------------------------------------------------------

CLAIM A — "forge.verify()'s verdict can no longer depend on which script called
it, because the interpreter is resolved in one place and no longer inherited from
sys.executable."
  BROKEN, in one concrete case: dataset_gate.verify_py() falls through to
  `return sys.executable` when .venv-train\Scripts\python.exe does not exist, and
  four of the five tests in tests/test_verifier_pin.py report as passes in that
  same state (F4). The red witness itself is sound and I could not break it — 310
  completions, banked once, two real launchers, 18 disagreements all one way,
  cause identified to a specific PEP with a minimal discriminating probe, and the
  green witness replays the same 310. That is a model red/green pair and I am not
  going to pretend otherwise. What is not sound is the SCOPE SENTENCE: it names
  unenumerated 3.11<->3.14 semantics, packages, OS and CPU, and omits the one
  failure mode that is readable in the eight lines of the function doing the
  pinning. Restate Claim A as: "the verdict cannot depend on the launcher WHILE
  .venv-train exists; if it does not exist, the pin silently degrades to the old
  behaviour and no test fails." Then fix that.
  Second, weaker attack: interpreter_fingerprint() records only the version
  string, obtained by running the interpreter, and on any failure records
  "python unknown" without raising (dataset_gate.py:114-118). A broken pinned
  interpreter therefore produces a self-consistent receipt: recorded "unknown"
  equals on-disk "unknown", the gate's equality check passes, and training
  proceeds. The DIRECTIVE's caveat covers packages but not this.

NON-CLAIM 1, "not claiming independence holds for the TRAINED arm": stronger than
the executor realises — it does not hold for the NULL arm either, at the
prediction that matches the instrument (F1). Accept and sharpen.

NON-CLAIM 2, "not claiming the 57 historical eval_history runs are unaffected":
correctly hedged, and its supporting measurement (section 74) is conditional on
F5. If the replay was in-process, the non-claim is fine but its evidence is
vacuous.

NON-CLAIM 3, "not claiming the 4 out-of-band tasks are harmless": correct not to
drop them, and I endorse the selection-regress reasoning explicitly. But the
harm is quantified nowhere and it is 13% of any effect (F9). "Not harmless" plus
a number is a much stronger position than "not harmless".

NON-CLAIM 4, "not claiming the ruler supports a generalisation claim": checked
downstream for a contradiction and found NONE in code. Nothing computes a
population-level claim; screen_tasks.py:78-81 states the estimand correctly
("the formula estimates the change in mean pass rate ON THESE T TASKS ... Claiming
'the model improved at code generation' needs an extra tau^2/T heterogeneity term
this omits. Pre-register which estimand is meant."). The non-claim is honoured by
the code. It is NOT honoured by council/council-report-2026-07-25_0317.html:153
and the 1550 transcript, which read per-task eval_history as a "longitudinal
growth chart" where "families that move together reveal shared skill substrate" —
that is a generalisation reading of the same numbers, sitting in the same repo.
Those are old council artifacts, not current claims, so this is a housekeeping
note rather than a live contradiction: the interpretation the non-claim disowns is
on file, unretracted, and would be read as project belief by anyone arriving
later. Also note the irony worth keeping: "families that move together" is
exactly the positive inter-task correlation that F1 measures and Q2 warns will
inflate the trained arm's variance. The old council was pointing at a real thing
and drawing the wrong conclusion from it.

NON-CLAIM 5, "not claiming data/ruler_frozen.json is current": accurate, and F2
makes it sharper — the file is not merely stale in its rates, it is unread by any
consumer, so its currency has no operational consequence at all today. That is
worse than stale.

NON-CLAIM 6, "not claiming the noise floor is model-general": accurate and
adequately scoped. One model, one quantization; I add one thing it does not say —
it is also ONE SERVER SESSION PATTERN, which is O2.

--------------------------------------------------------------------------------
LEFTOVER RISKS — unresolved even if every fix above lands
--------------------------------------------------------------------------------
1. Training-seed variance is not reduced by any of this (O1). Even with three
   seeds you have an n=3 estimate of a variance, and section 73's own method note
   applies with full force: n=3 is a rumour when the quantity is a variance.
2. Cross-version verifier divergence beyond the annotation case stays
   unenumerated. A flashlight is the right description. The only real fence is
   running the candidate under BOTH interpreters and treating disagreement as a
   third outcome (neither pass nor fail) — expensive, and I am not recommending
   it, but it is the shape of an actual fence if this ever bites twice.
3. The interpreter fingerprint records a version string, not the environment:
   packages, OS, CPU, and — added here — whether the pin degraded to the launcher
   at all. Two "python 3.11.9" fingerprints are not the same verifier.
4. The 31 tasks are AceCode oss rows, generated by gpt-3.5-turbo-1106 per the
   dataset card (VERIFIED in section 59's round). Contamination is filtered only
   in the sense that memorised tasks score ~1.0 and get rejected by the band. A
   task the base model half-remembers lands squarely IN the band and looks ideal.
   The band is a contamination filter for total recall only.
5. I did not read tests/test_ruler_noise.py's seven scenarios line by line, so
   "the analyzer was checked against known answers" is CARRIED from the channel,
   not verified by me. The one part I did verify is that decompose()'s
   pred_greedy term uses eff_n = N^2/(N-1), which is the correct correction, and
   that the artifact's CAUSE-1 line reports the greedy constancy check as
   measured rather than assumed.
6. data/ruler_frozen.json itself was not opened by me. Every claim I make about
   it comes from cmd_freeze's code and the channel.
7. Nothing above addresses whether 13 prompts can produce any effect at all,
   which remains the project's largest open scientific question and is where
   Wang et al. 2504.20571 (CARRIED, still unacted) points.

--------------------------------------------------------------------------------
FIX CLASSES — the kind of change each finding needs, not the change itself
--------------------------------------------------------------------------------
A. INSTRUMENT DEFINITION, before the first efficacy run, because it is free now
   and never again: F3, F6, Q1. Change what is sampled and what is scored;
   declare one primary endpoint. One-time cost ~100 minutes of null-arm
   re-measurement.
B. ENFORCEMENT — a receipt that nothing demands is not a pin: F2. A loader that
   refuses to build the ruler unless the reconstructed set hash equals
   ruler_frozen.json's. Pattern already exists in dataset_gate.require_verified.
   Close the CLASS: every pin artifact needs a refusing loader.
C. FAIL-CLOSED DEFAULTS AND HONEST SKIPS: F4, plus the fingerprint's silent
   "unknown" (Claim A, second attack). Absent .venv-train must raise or be
   recorded as UNPINNED and rejected by the gate; a skipped test must not be
   reportable as a pass.
D. CLAIM HYGIENE — the stale thing is the sentence, not the figure: F1, F7, F8,
   F11. Derive claim direction from the computed ratio; restate section 73's
   conclusion against the greedy-corrected null; re-derive SIZING's mean p(1-p)
   from the frozen ruler or annotate it as pilot-derived.
E. ZERO-COST DESIGN, all four free: O2 interleave arms run-by-run; O3 refuse
   partial rows rather than dropping tasks; Q2(d)1 Welch with each arm's own sd;
   Q2(d)2 pre-commit to reporting the CI and the achieved sensitivity.
F. BUDGET REALLOCATION, not increase: O1/R7. Three seeds at k=12 costs less than
   one seed at k=25 and measures a variance component that k cannot touch.
G. PREREGISTRATION, one document, one hour: O4. Primary endpoint, both estimands
   (31-task and 27-live-task, F9), direction, decision rule, and the analysis —
   signed before the run.
H. VERIFICATION OF A PAST MEASUREMENT, one minute: F5. Quote section 74's launch
   command, and add an assert to the replay harness so the question cannot recur.

--------------------------------------------------------------------------------
THE QUESTIONS THEMSELVES — did activation #17 ask the right three?
--------------------------------------------------------------------------------
Q1 and Q3 are the right questions and Q3 is the sharpest question this channel
has asked: it noticed, unprompted, that a prior ruling had been invalidated by a
later ruling from the same source, and asked whether the budget was spent rather
than assuming either answer. Q2 is the right question with a hopeful thumb on the
scale — it asks whether entropy collapse makes the MDE conservative, and does not
ask what would make it optimistic, which is the direction the executor's own
+0.0102 correlation points and the one that costs money if wrong.

Four questions it should have asked and did not:
 1. "WHICH ENDPOINT IS PRIMARY, AND IS pass@3 EVEN A LIVE METRIC ON A BAND-
    SELECTED RULER?" This is the biggest omission. Everything measured in
    sections 70-73 — the noise floor, the decomposition, the MDE table, the
    SIZING block — is pass@1. eval.py still reports pass@3, measure.py still
    reads it, no prereg names one, and the arithmetic in F3 says pass@3 on this
    ruler has a floor of 0.6 on 71% of tasks and saturates at 0.87 at the ruler's
    own mean rate. Q1 asks "is pass@3 the quantity it names" as a sub-clause of a
    question about the estimator. It is the whole question.
 2. "HOW MANY TIMES WILL I TRAIN, AND WHAT IS THE VARIANCE OF THAT?" (O1.) The
    DIRECTIVE prices generation noise to three significant figures and never
    mentions that one training run is one sample of the intervention. This is the
    largest unpriced variance in the design and no amount of k reduces it.
 3. "IS ANYTHING ENFORCING THE FREEZE?" (F2.) Section 72 argued the freeze's
    design at length and correctly; nobody checked whether a consumer honours it.
    The project's own recurring lesson — a guard that is written is not a guard
    that is demanded — was available.
 4. "WHAT DOES verify_py() DO WHEN .venv-train ISN'T THERE?" (F4.) The DIRECTIVE
    enumerates the unknowns around Claim A carefully and misses the known one.

And one question NOT to ask, since the DIRECTIVE half-invited it: do not re-open
whether the 4 out-of-band tasks should be dropped. The executor's reasoning is
correct, the regress is real, and F9 shows the right response is to quote both
estimands, not to prune the ruler.

Finally, the executor's standing invitation, answered directly: yes, there is a
point estimate leaned on without its interval in sections 71-74, and it is in the
sentence doing the correcting. Section 73's "+0.0102 reinforcement" (and section
72's "-0.0072 cancellation" before it) is quoted with no interval anywhere, in a
section whose entire thesis is that a variance point estimate without its interval
is a rumour. The sd ratio against the greedy-corrected null is 1.169 with CI
[0.957, 1.500] — the covariance residual's sign is not established at n=40 either.
The method note should read: n=10 is a rumour when the quantity is a variance, and
so is n=40 when the quantity is a COVARIANCE, because a covariance is a variance
with a sign to get wrong as well.

--------------------------------------------------------------------------------
ONE RECOMMENDED NEXT PROMPT FOR THE PROPRIETOR TO HAND THE EXECUTOR
--------------------------------------------------------------------------------
"Section 75 is banked. Do these in this order, and do not start the efficacy run
until 1-4 are done.

 1. Answer one question in the channel before anything else: was section 74's
    SRLM_VERIFY_PY replay two separate processes, or one process with os.environ
    mutated after `import forge`? forge.py:126 binds VERIFY_PY at import time and
    dataset_gate caches the fingerprint, so if it was one process, section 74
    measured the same interpreter twice and its conclusion is unsupported. Quote
    the launch command. Then add `assert forge.VERIFY_PY == expected` to the
    replay harness so this can never be ambiguous again.

 2. Close the class the PhD found in dataset_gate.verify_py(): absent
    .venv-train, it returns sys.executable and the inherited-interpreter defect
    is silently back, while four of five tests in test_verifier_pin.py return
    early and read as passes. Red witness first: rename .venv-train, run the
    test file, and show it reporting green with the pin degraded. Then make it
    fail closed and make skips report as skips.

 3. Change the eval instrument now, while it is free, per section 75 Q1 option
    (C): 6 draws per task — 1 greedy RECORDED BUT NOT SCORED, 5 IID at temp 0.8
    — set KS = (1,), and re-measure the null arm's noise floor at 40 replicates
    under the new protocol (~100 minutes). Report the new sd with its CI, the
    ratio against BOTH the naive and the greedy-corrected independence
    predictions, and the new k for a 3pp MDE. State in the channel that section
    73's 'independence holds, 1.01x' was measured against the naive null and that
    the greedy-corrected ratio was 1.17x, CI [0.957, 1.500].

 4. Make the freeze enforceable: a loader that rebuilds the 31 tasks, recomputes
    the set sha256, compares it to data/ruler_frozen.json, and refuses to
    proceed on mismatch — same shape as dataset_gate.require_verified. Then
    freeze --force to re-issue the n=40 rates. And fix the banner in
    screen_tasks.py so the direction word is derived from the ratio instead of
    hardcoded per branch.

 5. Write the prereg before the first efficacy run. One page: primary endpoint
    (the redefined pass@1), both estimands (31-task mean primary, 27-live-task
    mean as sensitivity, effective MDE 3.5pp not 3.0pp), Welch with each arm's
    own sd from its own replicates, arms INTERLEAVED run-by-run not blocked, and
    a pre-committed decision rule stated as a confidence interval rather than a
    power promise.

 6. Then, instead of one arm pair at k=25, run 3 trained seeds + 1 null at k=12
    for fewer total generations, and report the between-seed spread. If three
    seeds disagree by more than 4pp, the single-seed k=25 run was never going to
    mean anything and you will have found that out for less money."
