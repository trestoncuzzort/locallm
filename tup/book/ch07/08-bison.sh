# 7.8. Bison-3.8.2
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter07/bison.html
# TUP_TARBALL=bison-3.8.2.tar.xz

./configure --prefix=/usr \
            --docdir=/usr/share/doc/bison-3.8.2

make

make install
