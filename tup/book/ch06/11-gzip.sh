# 6.11. Gzip-1.14
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter06/gzip.html
# TUP_PACKAGE=gzip-1.14

./configure --prefix=/usr --host=$LFS_TGT

make

make DESTDIR=$LFS install
