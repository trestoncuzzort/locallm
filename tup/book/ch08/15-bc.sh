# 8.15. Bc-7.0.3
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/bc.html
# TUP_PACKAGE=bc-7.0.3

CC='gcc -std=c99' ./configure --prefix=/usr -G -O3 -r

make

if tup_tests_enabled "bc"; then
make test
else tup_receipt_skip_tests "bc"; fi

make install
