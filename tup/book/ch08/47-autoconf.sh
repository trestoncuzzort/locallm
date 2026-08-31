# 8.47. Autoconf-2.72
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/autoconf.html
# TUP_PACKAGE=autoconf-2.72

./configure --prefix=/usr

make

if tup_tests_enabled "autoconf"; then
make check
else tup_receipt_skip_tests "autoconf"; fi

make install
