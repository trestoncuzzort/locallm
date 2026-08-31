# 6.10. Grep-3.12
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter06/grep.html
# TUP_PACKAGE=grep-3.12

./configure --prefix=/usr   \
            --host=$LFS_TGT \
            --build=$(./build-aux/config.guess)

make

make DESTDIR=$LFS install
