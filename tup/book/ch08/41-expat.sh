# 8.41. Expat-2.7.3
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/expat.html
# TUP_TARBALL=expat-2.7.3.tar.xz

./configure --prefix=/usr    \
            --disable-static \
            --docdir=/usr/share/doc/expat-2.7.3

make

if tup_tests_enabled "expat"; then
make check
else tup_receipt_skip_tests "expat"; fi

make install

install -v -m644 doc/*.{html,css} /usr/share/doc/expat-2.7.3
