"""Can the noise decomposition recover a dependence structure it was handed?

ruler_noise.decompose() is about to produce the number that sets the generation
budget for every future run (section 70's MDE table rests on it). A decomposition
that reports "observed sd is 2.9x under the independence prediction" is only
evidence if the same code returns ~1.0x on data that IS independent. So each
scenario below builds synthetic replicates whose structure is known by
construction, and asserts decompose() reads it back:

  A  independent draws                -> observed/predicted ~ 1.0, cov ~ 0
  B  greedy draw frozen per task       -> ~sqrt((N-1)/N)=0.894 vs the naive
                                          prediction, ~1.0 vs greedy-corrected
  C  shared per-run latent, same sign  -> observed >> predicted, cov_total > 0
  D  shared latent, balanced +/- signs -> cov_total < 0 but observed ~ predicted
  E  antithetic pairs, marginals fixed -> observed <  predicted, cov_total < 0
                                          (the section 62 A1b shortfall shape)

D AND E ARE BOTH NEGATIVE-COVARIANCE AND THEY DO NOT BEHAVE THE SAME, which is
the point of having both. In D the latent inflates every task's marginal variance
by c*Var(v) and contributes sum_{i!=j} Cov_ij = ((sum s_i)^2 - sum s_i^2)*c*Var(v)
= -T*c*Var(v) when sum(s_i)=0. Those two terms cancel EXACTLY in
Var(run mean) = (1/T^2)[sum_i Var_i + sum_{i!=j} Cov_ij], so the run-level sd comes
back at the binomial value despite genuine negative covariance. E instead couples
tasks antithetically through a shared uniform (task A passes if u < p_A, its
partner if 1-u < p_B), which leaves each marginal EXACTLY binomial and so produces
a real shortfall.

Consequence for reading the live result, and it is easy to get backwards:
"negative covariance" does not by itself predict an observed sd under the binomial
prediction. Only negative covariance AT UNINFLATED MARGINALS does. That is why
`analyze` reports the observed marginals separately from the covariance residual
rather than reporting one ratio.

Tolerances are loose on purpose. These assert that the instrument reads the right
SIGN and the right ORDER OF MAGNITUDE, which is what the conclusion rests on; they
are not a claim that a 400-run synthetic ratio pins the estimator to 1%.
"""
import math
import random
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ruler_noise as rn

N = 5
RATES = [0.2167, 0.2833, 0.3167, 0.3333, 0.3667, 0.3833, 0.4333, 0.45,
         0.5, 0.5333, 0.5667, 0.6333, 0.7, 0.7333, 0.7667, 0.7833]
TIDS = [f"t{i:02d}" for i in range(len(RATES))]
CONF = dict(zip(TIDS, RATES))


def _runs(sampler, R, seed=7):
    """Build R synthetic replicate rows in eval.evaluate's output shape.

    `ctx` carries whatever shared randomness a scenario needs: one gaussian
    latent per run, and one INDEPENDENT list of uniforms per task PAIR so the
    antithetic scenario couples partners without coupling everything.
    """
    rng = random.Random(seed)
    out = []
    frozen = {t: (1 if rng.random() < CONF[t] else 0) for t in TIDS}
    for r in range(1, R + 1):
        ctx = {"gauss": rng.gauss(0, 1),
               "pairs": {p: [rng.random() for _ in range(N)]
                         for p in range(len(TIDS) // 2 + 1)}}
        per_task = []
        for i, t in enumerate(TIDS):
            greedy, sampled = sampler(rng, t, i, frozen, ctx)
            per_task.append({"tid": t, "correct": greedy + sum(sampled),
                             "n": N, "requested": N, "gen_errors": 0,
                             "greedy": greedy, "sampled": sampled})
        out.append({"model": "synthetic", "task_set": rn.TASK_SET,
                    "n_samples": N, "n_tasks": len(TIDS), "replicate": r,
                    "gen_errors_total": 0, "per_task": per_task})
    return out


def _bern(rng, p):
    return 1 if rng.random() < max(0.0, min(1.0, p)) else 0


def _indep(rng, t, i, frozen, ctx):
    p = CONF[t]
    return _bern(rng, p), [_bern(rng, p) for _ in range(N - 1)]


def _frozen_greedy(rng, t, i, frozen, ctx):
    p = CONF[t]
    return frozen[t], [_bern(rng, p) for _ in range(N - 1)]


def _shared_same_sign(rng, t, i, frozen, ctx):
    p = CONF[t] + 0.15 * ctx["gauss"]
    return _bern(rng, p), [_bern(rng, p) for _ in range(N - 1)]


def _shared_balanced(rng, t, i, frozen, ctx):
    p = CONF[t] + (0.15 if i % 2 == 0 else -0.15) * ctx["gauss"]
    return _bern(rng, p), [_bern(rng, p) for _ in range(N - 1)]


def _antithetic(rng, t, i, frozen, ctx):
    """Partner tasks share a uniform, one reading it forward and one reversed.
    Each marginal stays EXACTLY Bernoulli(p) -- P(u < p) = P(1-u < p) = p -- so
    the negative dependence shows up purely as covariance, with no inflation of
    the per-task variances to hide behind."""
    p, us = CONF[t], ctx["pairs"][i // 2]
    draws = [(1 if (u if i % 2 == 0 else 1.0 - u) < p else 0) for u in us]
    return draws[0], draws[1:]


def test_independent_draws_read_back_as_independent():
    d = rn.decompose(_runs(_indep, 400, seed=11), CONF)
    ratio = d["sd_obs"] / d["pred_obsm"]
    assert 0.88 < ratio < 1.12, f"independent data read back at {ratio:.3f}x"
    # cov_total should be small next to the diagonal it is compared against
    assert abs(d["cov_total"]) < 0.35 * d["sum_var"], \
        f"spurious covariance {d['cov_total']:+.4f} vs sum_var {d['sum_var']:.4f}"


def test_frozen_greedy_is_attributed_to_the_greedy_draw():
    d = rn.decompose(_runs(_frozen_greedy, 400, seed=12), CONF)
    naive = d["sd_obs"] / d["pred_obsm"]
    corrected = d["sd_obs"] / d["pred_greedy"]
    expected = math.sqrt((N - 1) / N)          # 0.894
    assert abs(naive - expected) < 0.12, \
        f"frozen greedy gave {naive:.3f}x vs naive, expected ~{expected:.3f}"
    assert 0.88 < corrected < 1.12, \
        f"greedy-corrected prediction should absorb it, got {corrected:.3f}x"
    assert not d["greedy_flipped"], \
        "a frozen greedy draw must be reported as constant"


def test_greedy_flips_are_detected_when_greedy_varies():
    d = rn.decompose(_runs(_indep, 60, seed=13), CONF)
    # With a random greedy draw at these rates, essentially every task should
    # flip across 60 runs. This is the control on the CAUSE 1 check: if it
    # cannot see variation, "greedy was constant" means nothing.
    assert len(d["greedy_flipped"]) >= len(TIDS) - 1, \
        f"only {len(d['greedy_flipped'])}/{len(TIDS)} flipped; check is blind"


def test_positive_correlation_is_detected():
    d = rn.decompose(_runs(_shared_same_sign, 300, seed=14), CONF)
    assert d["cov_total"] > 0, f"expected positive cov, got {d['cov_total']:+.4f}"
    ratio = d["sd_obs"] / d["pred_obsm"]
    assert ratio > 1.5, f"shared latent should inflate sd, got {ratio:.3f}x"


def test_balanced_latent_gives_negative_cov_but_no_shortfall():
    """The trap case. Genuine negative covariance, and yet the run-level sd is
    unchanged, because the same latent inflated every marginal by exactly what
    the covariance removes. If this test ever starts asserting a shortfall,
    someone has confused 'negative covariance' with 'observed below binomial'."""
    d = rn.decompose(_runs(_shared_balanced, 300, seed=15), CONF)
    assert d["cov_total"] < 0, \
        f"balanced signs must give negative cov, got {d['cov_total']:+.4f}"
    assert d["sum_var"] > 1.15 * d["binom_var"], \
        "the latent should have inflated the marginals; it did not"
    ratio = d["sd_obs"] / d["pred_obsm"]
    assert 0.85 < ratio < 1.15, \
        f"inflation and cancellation should offset; got {ratio:.3f}x"


def test_antithetic_pairs_produce_a_real_shortfall():
    """Negative covariance at UNINFLATED marginals -- the shape that would make
    section 70's independence prediction genuinely too pessimistic."""
    d = rn.decompose(_runs(_antithetic, 300, seed=16), CONF)
    assert d["cov_total"] < 0, \
        f"antithetic pairs must give negative cov, got {d['cov_total']:+.4f}"
    # marginals must NOT be inflated -- that is what separates this from D
    assert 0.85 < d["sum_var"] / d["binom_var"] < 1.15, \
        f"marginals moved ({d['sum_var'] / d['binom_var']:.3f}x); construction broken"
    ratio = d["sd_obs"] / d["pred_obsm"]
    assert ratio < 0.95, f"cancellation should deflate sd, got {ratio:.3f}x"


def test_decompose_reproduces_section_70_prediction():
    """pred_conf must equal the published 0.0376 when handed the real artifact's
    31 confirmed rates, independent of whatever the replicates say."""
    import json
    spec = json.loads(rn.RULER.read_text(encoding="utf-8"))
    conf = {k["tid"]: k["confirmed_rate"] for k in spec["kept"]}
    tids = sorted(conf)
    fake = _runs(_indep, 4, seed=1)
    # re-key the synthetic rows onto the real tids so pred_conf uses real rates
    for r in fake:
        r["per_task"] = [dict(p, tid=t) for p, t in zip(
            (r["per_task"] * 3)[:len(tids)], tids)]
        r["n_tasks"] = len(tids)
    d = rn.decompose(fake, conf)
    assert d["T"] == 31, f"expected 31 confirmed tasks, got {d['T']}"
    assert round(d["pred_conf"], 4) == 0.0376, \
        f"independence prediction {d['pred_conf']:.4f} != section 70's 0.0376"


if __name__ == "__main__":
    fails = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print(f"PASS {name}")
            except AssertionError as e:
                fails.append(name); print(f"FAIL {name}: {e}")
    print(f"\n{len(fails)} failed")
    raise SystemExit(1 if fails else 0)
