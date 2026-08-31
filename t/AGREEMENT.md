# t cross-kernel agreement — 2026-08-31 07:17Z

Cell = real outcome / twin outcome. Agreement means `verified / refuted` in every present column.

| task | dafny | verus | spark |
|---|---|---|---|
| abs | verified / refuted | verified / refuted | verified / refuted |
| max | verified / refuted | verified / refuted | verified / refuted |

Backends:
- dafny: dafny 4.11.0
- verus: verus 0.2026.08.30.b432e82
- spark: gnatprove FSF 16.1.0 / Why3 for gnatprove version 1.8.2+git

Verdict basis: every source file hashed; e.g. `abs.dfy` 9fe1e7e805cfacce…, `abs.rs` 4411ed95f8c487e8…
