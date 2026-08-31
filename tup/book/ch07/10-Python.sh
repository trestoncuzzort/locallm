# 7.10. Python-3.14.0
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter07/Python.html
# TUP_TARBALL=Python-3.14.0.tar.xz

./configure --prefix=/usr       \
            --enable-shared     \
            --without-ensurepip \
            --without-static-libpython

make

make install
