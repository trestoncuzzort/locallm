#!/usr/bin/env python3
"""eval_heldin.py — the HELD-IN check. Scores forge.SEED_TASKS, not the ruler.

WHY THIS EXISTS. eval.py's HELD_OUT bank is deliberately disjoint from
SEED_TASKS, which makes it the right instrument for "did the model improve" and
the wrong one for "did the training do anything at all". Those are different
questions and a null answer to the second is not a null answer to the first.

Council section 59 measured that data/dpo_pairs_capped.jsonl is 918 pairs over
THIRTEEN distinct prompts - all of SEED_TASKS - so a held-out null has three
candidate causes it cannot separate:

    1. training genuinely does nothing at 13 prompts
    2. training works but LoRA r=16 cannot express it
    3. training works in-distribution but does not transfer

Scoring the 13 training prompts themselves separates cause 3 from causes 1-2,
and costs 13 tasks x N_SAMPLES generations rather than a screening run.

THIS IS NOT A RULER AND MUST NEVER BE REPORTED AS ONE. The model trained on
these exact prompts; movement here is partly memorisation and is expected to
overstate any real capability gain. It is a diagnostic, so its results go to
their own file and carry task_set="held_in" so they cannot be appended into
eval_history.jsonl or compared against a held-out number.

Run:  python eval_heldin.py                    # scores forge.MODEL_NAME
      python eval_heldin.py llama3-forged      # scores a trained model
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import eval as ruler
import forge

OUT = Path(__file__).with_name("data") / "heldin_history.jsonl"


def main() -> None:
    tag = sys.argv[1] if len(sys.argv) > 1 else forge.MODEL_NAME
    tasks = forge.SEED_TASKS
    print(f"HELD-IN check: scoring '{tag}' on {len(tasks)} SEED_TASKS "
          f"({ruler.N_SAMPLES} samples each). Diagnostic, NOT the ruler.\n")
    result = ruler.evaluate(tag, tasks=tasks, task_set="held_in")
    if not result:
        return
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(f"\naggregate (held-in, memorisation-inflated): {result['aggregate']}")
    print(f"appended to {OUT}")


if __name__ == "__main__":
    main()
