# 8.67. Gzip-1.14
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/gzip.html
# TUP_PACKAGE=gzip-1.14

./configure --prefix=/usr

make

if tup_tests_enabled "gzip"; then
make check
else tup_receipt_skip_tests "gzip"; fi

make install
