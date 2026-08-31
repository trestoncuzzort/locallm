#!/bin/bash
# OVERRIDE ch08/74-vim: the page ends with `vim -c ':options'`, which OPENS
# THE EDITOR so a human can look at vim's settings. Under the driver it reads
# EOF from /dev/null and dies. The line becomes a no-op; every other byte of
# the page (including the /etc/vimrc heredoc) is the book's own.
set -e
PAGE=""
for c in /tup-build/book/ch08/74-vim.sh /home/lfs/book/ch08/74-vim.sh; do
  [ -s "$c" ] && { PAGE="$c"; break; }
done
[ -n "$PAGE" ] || { echo "override: cannot find the vim page"; exit 1; }
sed "s@^vim -c ':options'\$@: # interactive options browser skipped by the driver@" \
  "$PAGE" | bash -e
