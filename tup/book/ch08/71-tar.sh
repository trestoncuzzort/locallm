# 8.73. Tar-1.35
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/tar.html
# TUP_PACKAGE=tar-1.35

FORCE_UNSAFE_CONFIGURE=1  \
./configure --prefix=/usr

make

if tup_tests_enabled "tar"; then
make check
else tup_receipt_skip_tests "tar"; fi

make install
make -C doc install-html docdir=/usr/share/doc/tar-1.35
