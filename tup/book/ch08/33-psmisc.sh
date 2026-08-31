# 8.33. Psmisc-23.7
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/psmisc.html
# TUP_TARBALL=psmisc-23.7.tar.xz

./configure --prefix=/usr

make

if tup_tests_enabled "psmisc"; then
make check
else tup_receipt_skip_tests "psmisc"; fi

make install
