# 6.12. Make-4.4.1
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter06/make.html
# TUP_TARBALL=make-4.4.1.tar.gz

./configure --prefix=/usr   \
            --host=$LFS_TGT \
            --build=$(build-aux/config.guess)

make

make DESTDIR=$LFS install
