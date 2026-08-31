# 8.51. Libffi-3.5.2
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/libffi.html
# TUP_PACKAGE=libffi-3.5.2

./configure --prefix=/usr    \
            --disable-static \
            --with-gcc-arch=native

make

if tup_tests_enabled "libffi"; then
make check
else tup_receipt_skip_tests "libffi"; fi

make install
