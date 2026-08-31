# 8.14. M4-1.4.20
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/m4.html
# TUP_PACKAGE=m4-1.4.20

./configure --prefix=/usr

make

if tup_tests_enabled "m4"; then
make check
else tup_receipt_skip_tests "m4"; fi

make install
