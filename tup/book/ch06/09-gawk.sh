# 6.9. Gawk-5.3.2
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter06/gawk.html
# TUP_PACKAGE=gawk-5.3.2

sed -i 's/extras//' Makefile.in

./configure --prefix=/usr   \
            --host=$LFS_TGT \
            --build=$(build-aux/config.guess)

make

make DESTDIR=$LFS install
