# 8.43. Less-685
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/less.html
# TUP_PACKAGE=less-685

./configure --prefix=/usr --sysconfdir=/etc

make

if tup_tests_enabled "less"; then
make check
else tup_receipt_skip_tests "less"; fi

make install
