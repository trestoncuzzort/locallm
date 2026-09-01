From Stdlib Require Import ZArith Lia.
Open Scope Z_scope.

Definition abs_t (x : Z) : Z := if (x <? 0) then (-x) else x.

Theorem abs_t_spec : forall (x : Z), ((abs_t x) >= 0) /\ (((abs_t x) = x) \/ ((abs_t x) = (-x))).
Proof.
  intros; unfold abs_t;
  repeat match goal with
  | |- context [?a <? ?b] => destruct (Z.ltb_spec a b)
  | |- context [?a <=? ?b] => destruct (Z.leb_spec a b)
  | |- context [?a =? ?b] => destruct (Z.eqb_spec a b)
  | |- _ => progress (cbn [orb andb negb])
  end; lia.
Qed.

Print Assumptions abs_t_spec.
