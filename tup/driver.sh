#!/bin/bash
# driver.sh — run one extracted chapter of the tup build, with receipts.
#
#   bash driver.sh <chapter-dir> [start-after]
#
# Reads <chapter-dir>/ORDER and executes each page script in order. State
# lives in $LFS/sources/log/driver.state (one line per completed script), so
# a rerun resumes after the last success — a failed page is retried, never
# skipped. Every page appends one JSON line to log/receipts.jsonl: page,
# package, seconds, exit status, and the sha256 of its own log. That ledger,
# not this script's stdout, is the record.
#
# Page contract (written by extract_book.py):
#   # TUP_PACKAGE=name-version -> tarball extracted fresh, cwd inside it,
#                                 tree deleted afterward (the book's standing
#                                 per-package instruction).
#   # TUP_ACTION_PAGE          -> run with cwd $LFS/sources, no wrapping.
# An executable $TUP_OVERRIDES/<page>.sh replaces the page body entirely.
#
# Test policy (ruling 2026-08-31, "mathematically useful, zero bullshit"):
# TUP_TESTS names the packages whose suites run; every other suite hit is
# receipted as tests_skipped, never silently dropped.
set -u
LFS=${LFS:-/mnt/lfs}
LOG=$LFS/sources/log
STATE=$LOG/driver.state
RECEIPTS=$LOG/receipts.jsonl
TUP_TESTS=${TUP_TESTS:-"glibc gcc binutils"}
TUP_OVERRIDES=${TUP_OVERRIDES:-/home/lfs/overrides}
CHDIR=$1
CH=$(basename "$CHDIR")
mkdir -p "$LOG"
touch "$STATE"

tup_tests_enabled() {
  for t in $TUP_TESTS; do case "$1" in *"$t"*) return 0;; esac; done
  return 1
}
tup_receipt_skip_tests() {
  echo "{\"ts\":\"$(date -u +%FT%TZ)\",\"page\":\"$1\",\"tests_skipped\":true}" >> "$RECEIPTS"
  echo "    [tests skipped by policy: $1]"
}
export -f tup_tests_enabled tup_receipt_skip_tests
export RECEIPTS

# ORDER is read on fd 3, and every page runs with stdin from /dev/null. A book
# page that reads stdin (createfiles does) would otherwise consume the ORDER
# list off fd 0 and then run the remaining filenames as commands — measured
# 2026-08-31: chapter 7 failed with "07-gettext.sh: command not found" x6.
while read -r script <&3; do
  id="$CH/$script"
  grep -qxF "$id" "$STATE" && continue
  page="${script%.sh}"
  src="$CHDIR/$script"
  # Chapter-qualified first: 05-glibc.sh names a page in BOTH chapter 5 and
  # chapter 8, and they are different builds. A flat name would fire the
  # wrong override on the wrong page, silently.
  ov=""
  for cand in "$TUP_OVERRIDES/${CH%%-*}/$page.sh" "$TUP_OVERRIDES/$page.sh"; do
    [ -x "$cand" ] && { ov="$cand"; break; }
  done
  if [ -n "$ov" ]; then src="$ov"; echo ">>> $id (OVERRIDE ${ov##*/overrides/})"
  else echo ">>> $id"; fi
  pkg=$(sed -n 's/^# TUP_TARBALL=//p' "$CHDIR/$script" | head -1)
  plog="$LOG/$CH-$page.log"
  t0=$SECONDS

  if [ -n "$pkg" ]; then
    tarball="$LFS/sources/$pkg"
    if [ ! -s "$tarball" ]; then
      echo "!!! $id: tarball absent: $pkg" | tee -a "$plog"; exit 1
    fi
    # the top-level dir comes from the tarball's own listing — filename
    # surgery guesses wrong on tcl8.6.17-src and friends
    top=$(tar tf "$tarball" 2>/dev/null | head -1 | cut -d/ -f1)
    dir="$LFS/sources/$top"
    ( set -e; cd "$LFS/sources"
      rm -rf "$dir"; tar xf "$tarball"; cd "$dir"
      bash -e "$src"
    ) > "$plog" 2>&1 < /dev/null
    rc=$?
    [ $rc -eq 0 ] && rm -rf "$dir"
  else
    ( set -e; cd "$LFS/sources"; bash -e "$src" ) > "$plog" 2>&1 < /dev/null
    rc=$?
  fi

  secs=$((SECONDS - t0))
  lhash=$(sha256sum "$plog" | cut -d' ' -f1)
  echo "{\"ts\":\"$(date -u +%FT%TZ)\",\"page\":\"$id\",\"package\":\"${pkg:-null}\",\"seconds\":$secs,\"exit\":$rc,\"log_sha256\":\"$lhash\"}" >> "$RECEIPTS"
  if [ $rc -ne 0 ]; then
    echo "!!! $id FAILED (exit $rc, ${secs}s) — last lines of $plog:"
    tail -15 "$plog"
    exit 1
  fi
  echo "$id" >> "$STATE"
  echo "    ok in ${secs}s"
done 3< "$CHDIR/ORDER"
echo "=== $CH complete"
