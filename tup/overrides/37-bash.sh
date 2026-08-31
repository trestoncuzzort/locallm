#!/bin/bash
# OVERRIDE ch08/37-bash: same exec-to-login pattern as ch07 createfiles.
set -e
PAGE=$(ls /tup-build/book/ch08/*-bash.sh 2>/dev/null | head -1)
sed 's|^exec /usr/bin/bash --login$|: # exec-to-login skipped under the driver|' "$PAGE" | bash -e
