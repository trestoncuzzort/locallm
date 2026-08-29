# srlm-forge — RETIRED

**Status: dead.** This project is no longer developed or maintained, as of
2026-08-29. Nothing here is being updated and there is no support. The full
working record — code, run logs, the project channel, and the manuscript
chain — is preserved in this repository's git history for reference only. The
last manuscript revision is `docs/revision-2026-08-25/manuscript-v15.md`.

The local working copies were removed from the machine after this commit; this
repository is the surviving record.

---

## What it was

An execution-verified preference pipeline. A language model wrote code; the code
was run against hidden unit tests; the candidate that actually passed became
`chosen`, a worse one `rejected`, and the pair became DPO preference-training
data — LoRA on an 8-billion-parameter model, scored on a frozen 31-task
benchmark. The wager was that the domain-specific part of such a loop is
essentially one function: the thing that decides whether a candidate is correct.

## What it actually established

It never produced an efficacy result. Nothing here shows the loop makes a model
better, and that never changed. What it produced instead was a rigorous,
preregistered account of how such a pipeline misleads the person running it:

- **A preregistered null that did not reproduce** on retraining, with roughly
  half of the apparent retrain gain decomposed to a *verifier artifact* — a
  pinned interpreter rejecting correct-but-un-annotated code, so the model
  learned to satisfy the checker rather than the task.
- **A catalogue of measurement-integrity failures** in the plumbing between the
  interpreter's verdict and the training file: a forgeable verdict channel,
  interpreter-dependent ground truth, a line-ending-dependent receipt, a
  benchmark at its ceiling, a gate that had stopped parsing, and more.
- **A demonstrated verifier bypass.** A candidate that never solves the task is
  accepted as a full pass, with zero optimization pressure, by forging the
  verdict sentinel and reading the grader's state out of its own execution
  frame.
- **An 8-bit optimizer artifact.** The base model's massive-activation channel
  sets its quantization block's scale, underflowing its neighbours' Adam
  second moments to exactly zero and driving coordinates past Adam's own
  per-coordinate displacement bound — with gradient dynamic range, not
  activation magnitude, predicting the damage.
- **An upstream initialization defect** in the training stack: the LoRA adapter
  is drawn before the trainer sets the seed, so a recorded seed does not govern
  initialization (observed across many TRL releases).

## Why it stopped

The efficacy question came back null, and the measurement-integrity and
false-verifier framings that were the real contribution were substantially
overtaken by concurrent 2026 work in reinforcement learning from verifiable
rewards. The project's remaining edge was rigor rather than novelty, and it has
been retired rather than repositioned. It is left here as a record, not a living
line of work.

---

*If you are reading this looking for the results themselves, they are in the
manuscript and the git history, both of which remain intact.*
