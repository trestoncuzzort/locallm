From Stdlib Require Import ZArith Lia.
Open Scope Z_scope.

Definition max_t (x : Z) (y : Z) : Z := if (y <=? x) then x else y.

Theorem max_t_spec : forall (x : Z) (y : Z), ((max_t x y) >= x) /\ ((max_t x y) >= y) /\ (((max_t x y) = x) \/ ((max_t x y) = y)).
Proof.
  intros; unfold max_t;
  repeat match goal with
  | |- context [?a <? ?b] => destruct (Z.ltb_spec a b)
  | |- context [?a <=? ?b] => destruct (Z.leb_spec a b)
  | |- context [?a =? ?b] => destruct (Z.eqb_spec a b)
  | |- _ => progress (cbn [orb andb negb])
  end; lia.
Qed.

Print Assumptions max_t_spec.
