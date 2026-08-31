# 6.2. M4-1.4.20
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter06/m4.html
# TUP_PACKAGE=m4-1.4.20

./configure --prefix=/usr   \
            --host=$LFS_TGT \
            --build=$(build-aux/config.guess)

make

make DESTDIR=$LFS install
