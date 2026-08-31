# 8.62. Diffutils-3.12
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/diffutils.html
# TUP_PACKAGE=diffutils-3.12

./configure --prefix=/usr

make

if tup_tests_enabled "diffutils"; then
make check
else tup_receipt_skip_tests "diffutils"; fi

make install
