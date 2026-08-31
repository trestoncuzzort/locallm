# 8.24. MPC-1.3.1
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/mpc.html
# TUP_PACKAGE=mpc-1.3.1

./configure --prefix=/usr    \
            --disable-static \
            --docdir=/usr/share/doc/mpc-1.3.1

make
make html

if tup_tests_enabled "mpc"; then
make check
else tup_receipt_skip_tests "mpc"; fi

make install
make install-html
