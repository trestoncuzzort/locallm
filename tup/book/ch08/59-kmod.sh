# 8.60. Kmod-34.2
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/kmod.html
# TUP_PACKAGE=kmod-34.2

mkdir -p build
cd       build

meson setup --prefix=/usr ..    \
            --buildtype=release \
            -D manpages=false

ninja

ninja install
