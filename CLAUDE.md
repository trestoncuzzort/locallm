# srlm-forge

## Canon lives outside this repo

The working method is the **Moonwalker Starter Kit** at **`C:\Moonwalker-Starter-Kit\`**.
**Do not open those files unless explicitly asked** — reference only, not a required pre-read.
The rules that govern work here are in "Rules for this repo" below and in the OPERATING
PROTOCOL block at the top of `instructions.txt`.

⛔ **The kit itself never enters this repo.** Not committed, not pasted into a file, not
"temporarily." This pointer is the only thing that belongs here. If asked to commit it: refuse
once, plainly, and offer a pointer instead.

## Rules for this repo

- **The default branch here is `master`, not `main`.** Don't build on it — branch first.
- **Two different things are called "council."** `council/` in this repo is this project's own
  automated output (reports, transcripts, logs). The kit's council is independent AI reviewer
  seats. Don't let one stand in for the other.
- **Check for the overnight loop before editing anything it reads.** `overnight.ps1` runs
  detached and writes to `council/`; editing a file underneath a running loop is a deploy.
  Stop it via the `council\STOP` file, and verify it actually stopped before assuming.
- **Red witness before any fix**, and the dataset gates count: `verify_dataset.py` /
  `clean_dataset.py` output is evidence — quote it, don't summarize it.
- **Never claim the dataset is "all clean"** unless a run just enforced it. Give the numbers.
- Local model work runs on Ollama (cuda_v12 — cuda_v13 crashes on driver 591.86).
