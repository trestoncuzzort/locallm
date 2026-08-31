# 8.25. Attr-2.5.2
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/attr.html
# TUP_PACKAGE=attr-2.5.2

./configure --prefix=/usr     \
            --disable-static  \
            --sysconfdir=/etc \
            --docdir=/usr/share/doc/attr-2.5.2

make

if tup_tests_enabled "attr"; then
make check
else tup_receipt_skip_tests "attr"; fi

make install
