# 8.84. SysVinit-3.14
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/sysvinit.html
# TUP_TARBALL=sysvinit-3.14.tar.xz

patch -Np1 -i ../sysvinit-3.14-consolidated-1.patch

make

make install
