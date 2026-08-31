# 6.4. Bash-5.3
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter06/bash.html
# TUP_TARBALL=bash-5.3.tar.gz

./configure --prefix=/usr                      \
            --build=$(sh support/config.guess) \
            --host=$LFS_TGT                    \
            --without-bash-malloc

make

make DESTDIR=$LFS install

ln -sv bash $LFS/bin/sh
