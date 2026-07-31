"""domains/ — the second instance, built so the seam can be DISCOVERED.

WHY THIS EXISTS. forge.py is one domain (Python functions checked by asserts) and
a seam designed against one instance is a guess. Council activation #18 asked for
prior art first and got a split answer: the reward-function SIGNATURE has
converged across TRL, veRL, Prime Intellect's `verifiers` and Reasoning Gym -- a
callable taking the completion plus a bag of task data and returning a float --
while the EXECUTION substrate has not converged at all, and that is the hard half.

So nothing is adopted as a dependency. What is adopted is the DECOMPOSITION that
`verifiers` v1 arrived at, because it names the thing that made verify() look
hard:

    TASKSET   what the work IS      -- prompts, ground truth, identity
    HARNESS   how it is SOLVED      -- the system prompt, extraction
    RUNTIME   where the check RUNS  -- isolation, timeout, resource identity

forge.verify() is two of those wearing one coat: a scoring predicate and an
execution substrate. Split them and the scoring predicate is easy in any domain,
while the genuinely hard engineering (isolation, timeout, pinning) concentrates
in one component that has nothing to do with the domain at all.

WHAT THIS IS NOT. It is not a second product and it is not a plugin framework.
It is an INSTRUMENT for finding out what forge.py's interface would actually have
to grow, by writing a real second verifier and recording the diff. The diff is the
deliverable. Do not generalise these modules into a framework before a third
domain exists -- that is the shape 05-STAYING-OUT-OF-THE-MUD warns about, and the
history of venv_guard in this repo (sections 65/67) is the local version of it.

HARD RULE, and it is the point of the exercise: nothing under domains/ may import
from forge.py. Reusing ACTOR_SYSTEM would make the prompt contract look
domain-general when it is the fifth Python-welded site (section 84). The two
system prompts are written independently and then DIFFED; every sentence they
share is a candidate parameter of the harness interface, and every sentence they
do not share is evidence the interface has to carry it. tests/test_sql_domain.py
fails if the import ever appears.
"""
