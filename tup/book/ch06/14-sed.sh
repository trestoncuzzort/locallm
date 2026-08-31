# 6.14. Sed-4.9
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter06/sed.html
# TUP_PACKAGE=sed-4.9

./configure --prefix=/usr   \
            --host=$LFS_TGT \
            --build=$(./build-aux/config.guess)

make

make DESTDIR=$LFS install
