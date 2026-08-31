# 6.8. Findutils-4.10.0
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter06/findutils.html
# TUP_PACKAGE=findutils-4.10.0

./configure --prefix=/usr                   \
            --localstatedir=/var/lib/locate \
            --host=$LFS_TGT                 \
            --build=$(build-aux/config.guess)

make

make DESTDIR=$LFS install
