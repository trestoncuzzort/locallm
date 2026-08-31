# 6.15. Tar-1.35
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter06/tar.html
# TUP_PACKAGE=tar-1.35

./configure --prefix=/usr   \
            --host=$LFS_TGT \
            --build=$(build-aux/config.guess)

make

make DESTDIR=$LFS install
