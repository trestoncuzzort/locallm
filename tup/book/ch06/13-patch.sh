# 6.13. Patch-2.8
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter06/patch.html
# TUP_TARBALL=patch-2.8.tar.xz

./configure --prefix=/usr   \
            --host=$LFS_TGT \
            --build=$(build-aux/config.guess)

make

make DESTDIR=$LFS install
