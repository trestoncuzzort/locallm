# 8.8. Xz-5.8.1
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/xz.html
# TUP_PACKAGE=xz-5.8.1

./configure --prefix=/usr    \
            --disable-static \
            --docdir=/usr/share/doc/xz-5.8.1

make

if tup_tests_enabled "xz"; then
make check
else tup_receipt_skip_tests "xz"; fi

make install
