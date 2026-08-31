#!/bin/bash
# OVERRIDE ch08/30-gcc: record the suite; do NOT invent a pass criterion.
#
# The book is explicit that no mechanical rule is available here: "A few
# unexpected failures cannot always be avoided", "On ARM64, many tests in the
# c-c++-common/hwasan directory are known to fail", "In some cases test
# failures depend on the specific hardware of the system." It offers a
# summary-extraction recipe and a comparison against published results — a
# human judgment, not a threshold.
#
# tup will not fabricate one. The suite RUNS (it is the largest evidence this
# compiler works), every FAIL line is banked to a named file, the expected-pass
# and unexpected-failure counts go into the receipt, and the receipt says
# "RECORDED, NOT JUDGED" in those words. Inventing a passing threshold the
# book declines to give would be a number that looks like a verdict and is
# not one — the exact thing this repository exists to refuse.
set -e
. /tup-build/overrides/lib-judge.sh
PAGE=/tup-build/book/ch08/30-gcc.sh
[ -s "$PAGE" ] || { echo "override: gcc page missing"; exit 1; }
sed 's@^su tester -c "PATH=\$PATH make -k check"$@judge_record_only ch08-30-gcc su tester -c "PATH=$PATH make -k check"@' \
  "$PAGE" > /tmp/gcc-judged.sh
grep -q "judge_record_only" /tmp/gcc-judged.sh || { echo "override: substitution failed"; exit 1; }
. /tmp/gcc-judged.sh
