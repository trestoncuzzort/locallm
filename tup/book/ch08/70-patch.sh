# 8.72. Patch-2.8
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/patch.html
# TUP_PACKAGE=patch-2.8

./configure --prefix=/usr

make

if tup_tests_enabled "patch"; then
make check
else tup_receipt_skip_tests "patch"; fi

make install
