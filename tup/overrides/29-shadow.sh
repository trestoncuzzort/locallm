#!/bin/bash
# OVERRIDE ch08/29-shadow: `passwd root` prompts a terminal. Initial root
# password is set non-interactively to "tup" — CHANGE IT AT FIRST BOOT; the
# receipt records that this override exists precisely so nobody pretends the
# password was chosen well.
set -e
PAGE=$(ls /tup-build/book/ch08/*-shadow.sh 2>/dev/null | head -1)
sed 's|^passwd root$|echo root:tup \| chpasswd   # initial password, change at first boot|' "$PAGE" | bash -e
