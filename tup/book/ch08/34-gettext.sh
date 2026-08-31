# 8.34. Gettext-0.26
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/gettext.html
# TUP_PACKAGE=gettext-0.26

./configure --prefix=/usr    \
            --disable-static \
            --docdir=/usr/share/doc/gettext-0.26

make

if tup_tests_enabled "gettext"; then
make check
else tup_receipt_skip_tests "gettext"; fi

make install
chmod -v 0755 /usr/lib/preloadable_libintl.so
