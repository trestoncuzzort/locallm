#!/bin/bash
# OVERRIDE ch07/06-createfiles: the book's `exec /usr/bin/bash --login` exists
# so a HUMAN re-enters the shell once /etc/passwd is real; under the driver it
# would replace the page's shell mid-page and silently skip every later block.
# The book's bytes run unchanged except that one line becomes a no-op.
set -e
PAGE=$(ls /tup-build/book/ch07-inner/*createfiles.sh /home/lfs/book/ch07/*createfiles.sh 2>/dev/null | head -1)
sed 's|^exec /usr/bin/bash --login$|: # exec-to-login skipped under the driver|' "$PAGE" | bash -e
