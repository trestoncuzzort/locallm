# prove 7: the Rocq STANDARD LIBRARY — a separate package since Rocq 9.
# Found the honest way: rocq-core built and installed clean, and then
# `Require Import ZArith` failed inside tup and the max task came back
# MALFORMED. The kernel without its stdlib can check proofs but cannot talk
# about arithmetic the way t's lowering speaks it (ZArith, lia).
# TUP_TARBALL=rocq-stdlib-9.2.0.tar.gz
export OCAMLPATH=$(ocamlfind printconf destdir)
dune build -p rocq-stdlib -j $(nproc)
dune install -p rocq-stdlib --prefix /usr
# the probe that failed before this page existed, now a gate:
printf 'Require Import ZArith Lia.\nOpen Scope Z_scope.\nGoal forall a b : Z, a <= b -> a <= b + 1. intros. lia. Qed.\n' > /tmp/stdlib-probe.v
coqc /tmp/stdlib-probe.v
rm -f /tmp/stdlib-probe.* 
echo "stdlib probe: ZArith + lia discharge a goal"
