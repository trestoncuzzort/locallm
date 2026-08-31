def abs_t (x : Int) : Int := (-x)

theorem abs_t_spec (x : Int) :
    ((abs_t x) ≥ (0 : Int)) ∧ (((abs_t x) = x) ∨ ((abs_t x) = (-x))) := by
  unfold abs_t; first | (split <;> omega) | omega

#print axioms abs_t_spec
