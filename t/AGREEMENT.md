# t cross-kernel agreement — 2026-08-31 12:36Z

Cell = real outcome / twin outcome. Agreement means `verified / refuted` in every present column.

| task | dafny | verus | spark | framac | lean | rocq |
|---|---|---|---|---|---|---|
| abs | verified / refuted | verified / refuted | verified / refuted | verified / refuted | verified / refuted | verified / refuted |
| all_nonneg | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error |
| contains | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error |
| count_matches | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error |
| factorial | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error |
| fib | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error |
| gcd | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error |
| linear_search | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error |
| max | verified / refuted | verified / refuted | verified / refuted | verified / refuted | verified / refuted | verified / refuted |
| seq_max | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error |
| sum_upto | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error | lower-error / lower-error |

Kernels present: 6 of 6 (dafny, verus, spark, framac, lean, rocq)

Backends:
- dafny: dafny 4.11.0
- verus: verus 0.2026.08.30.b432e82
- spark: gnatprove FSF 16.1.0 / Why3 for gnatprove version 1.8.2+git
- framac: frama-c 33.0 (Arsenic) / alt-ergo 2.4.3-free
- lean: Lean (version 4.33.1
- rocq: The Rocq Prover, version 9.2

Verdict basis: every source file hashed; e.g. `abs.dfy` 9fe1e7e805cfacce…, `abs.rs` 4411ed95f8c487e8…
