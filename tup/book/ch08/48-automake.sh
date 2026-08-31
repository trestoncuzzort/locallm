# 8.48. Automake-1.18.1
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/automake.html
# TUP_TARBALL=automake-1.18.1.tar.xz

./configure --prefix=/usr --docdir=/usr/share/doc/automake-1.18.1

make

if tup_tests_enabled "automake"; then
make -j$(($(nproc)>4?$(nproc):4)) check
else tup_receipt_skip_tests "automake"; fi

make install
