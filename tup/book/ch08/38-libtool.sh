# 8.38. Libtool-2.5.4
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/libtool.html
# TUP_PACKAGE=libtool-2.5.4

./configure --prefix=/usr

make

if tup_tests_enabled "libtool"; then
make check
else tup_receipt_skip_tests "libtool"; fi

make install

rm -fv /usr/lib/libltdl.a
