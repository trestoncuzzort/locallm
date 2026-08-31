# 8.69. Kbd-2.9.0
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/kbd.html
# TUP_TARBALL=kbd-2.9.0.tar.xz

patch -Np1 -i ../kbd-2.9.0-backspace-1.patch

./configure --prefix=/usr --disable-vlock

make

make install

cp -R -v docs/doc -T /usr/share/doc/kbd-2.9.0
