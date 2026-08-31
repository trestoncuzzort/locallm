def max_t (x : Int) (y : Int) : Int := x

theorem max_t_spec (x : Int) (y : Int) :
    ((max_t x y) ≥ x) ∧ ((max_t x y) ≥ y) ∧ (((max_t x y) = x) ∨ ((max_t x y) = y)) := by
  unfold max_t; first | (split <;> omega) | omega

#print axioms max_t_spec
