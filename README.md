# tup

**A Linux distribution built for AI work, where you can account for every byte
and `t`, a language whose programs carry machine-checked proofs.**

Most AI development environments are unaccountable piles. Nobody can tell you
what is actually inside their container, which weights are loaded, or what an
agent changed on disk last Tuesday. tup is the one where you can: every package
is built from hashed sources, every file in the system is inventoried, and every
layer says exactly what it added.

**Status: early.** The base system builds and the pieces below are real and
running, but tup is not yet installable on your laptop. What exists, what does
not, and what is merely intended are marked as such throughout that is the
habit the whole project is built on.

---

## The two halves

### tup the distribution

Built from source with a receipt on every step. No package manager: the
filesystem *is* the manifest, which is what makes "we know everything on this
system" a checkable claim rather than a slogan. Every command comes from the
Linux From Scratch book verbatim; every deviation is a separate, diffable file
that states why it exists.

See [`tup/`](tup/) for the build system, and [`tup/README.md`](tup/README.md)
for how it works and what it has already caught.

The intended shape is layered, each layer with its own inventory diff:

| Layer | What it adds | Status |
|---|---|---|
| **base** | kernel, libc, toolchain fully hashed | building |
| **agent** | Node, Claude Code AI tooling as a first-class citizen | planned |
| **train** | `locallm`, PyTorch train models on the box itself | `locallm/` exists |
| **prove** | `t` and its proof kernels | `t/` exists |
| **infer** | local model serving | planned |

### t the language

`t` is a **specification interlingua**: write a task once signature,
preconditions, postconditions and lower it mechanically to established
verifiers, whose kernels supply every verdict. t proves nothing itself and is
trusted for nothing. That is the design, not a weakness.

**Six independent proof kernels currently agree on every t program:**

| Kernel | Stack |
|---|---|
| Dafny 4.11 | .NET + Z3 |
| Verus 0.2026.08.30 | Rust + Z3 |
| GNATprove FSF 16.1 | Ada + Why3 + Z3 |
| Frama-C 33.0 | C/ACSL + alt-ergo |
| Lean 4.33.1 | kernel-checked proof terms |
| Rocq 9.2 | kernel-checked proof terms |

A task counts only on a **measured flip**: the real program verifies *and* a
deliberately broken twin is refuted. A twin that still verifies means the
specification is vacuous, and the task is refused. See [`t/`](t/) and
[`t/AGREEMENT.md`](t/AGREEMENT.md) for the current cross-kernel table.

Agda's adapter is measured and landed; its *lowering* is parked, because the
standard library has no decision procedure for t's arithmetic fragment and
hand-plumbed proofs dressed as automation would be exactly the unwitnessed
artifact t exists to refuse.

---

## Why these two things are one project

A proof is only as good as the machine that checked it, and a machine is only
as good as your knowledge of what is on it. t makes programs provable; tup
makes the ground they are proved on accountable. Neither is worth much alone:
a verified program on an unaccountable system is a proof about nothing in
particular, and an accountable system running unverified software is just
tidy.

The research that produced this discipline is in the repository root an
execution-verified DPO pipeline whose real finding was that roughly half of a
measured benchmark gain came from the measuring instrument rather than the
model. That work is **scaffolding, not law**: it taught the method, it is
written up in [`docs/revision-2026-08-25/`](docs/revision-2026-08-25/), and the
distro and the language are where the method goes next.

---

## What is honestly not true yet

- **tup is not installable on arbitrary hardware.** The current kernel is
  configured for a virtual machine (virtio drivers, no initramfs). Real devices
  need a generic kernel, an initramfs, firmware, and an installer. None of that
  is written.
- **tup is arm64 today.** The x86_64 build the one that matters for CUDA and
  for training is the same driver pointed at a different book, and has not
  been run.
- **tup 0.1 is witnessed, not verified.** Nothing here proves the kernel or
  libc correct. It records what was built, from which bytes, in what order.
- **t v0 is small on purpose:** integers, no quantifiers, no loops, one
  mutation operator. Expressiveness gates open with measurements, not
  intentions.

## Layout

| Path | What |
|---|---|
| [`tup/`](tup/) | the distribution's build system, overrides, receipts |
| [`t/`](t/) | the language, its lowerings, and its verifier adapters |
| [`locallm/`](locallm/) | train a model from scratch on your own machine (MIT) |
| [`ROADMAP.md`](ROADMAP.md) | what happens next, adversarially reviewed |
| repository root | the research pipeline and its instruments |
| [`docs/`](docs/) | manuscripts, review dossiers, port witnesses |

## License

[`locallm/`](locallm/) is MIT. The rest is the working research record;
third-party datasets keep their own licenses (KodCode is CC BY-NC and is never
redistributed from here; AceCode is MIT with attribution).

Copyright (c) 2026 Treston Malachi Cuzzort.
