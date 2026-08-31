# 8.2. Package Management
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/pkgmgt.html
# TUP_ACTION_PAGE

grep -l 'libfoo.*deleted' /proc/*/maps | tr -cd 0-9\\n | xargs -r ps u

./configure --prefix=/usr/pkg/libfoo/1.1
make
make install

./configure --prefix=/usr
make
make DESTDIR=/usr/pkg/libfoo/1.1 install
