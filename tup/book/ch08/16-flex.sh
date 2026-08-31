# 8.16. Flex-2.6.4
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/flex.html
# TUP_PACKAGE=flex-2.6.4

./configure --prefix=/usr    \
            --disable-static \
            --docdir=/usr/share/doc/flex-2.6.4

make

if tup_tests_enabled "flex"; then
make check
else tup_receipt_skip_tests "flex"; fi

make install

ln -sv flex   /usr/bin/lex
ln -sv flex.1 /usr/share/man/man1/lex.1
