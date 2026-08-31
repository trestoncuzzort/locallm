# 8.68. IPRoute2-6.17.0
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/iproute2.html
# TUP_TARBALL=iproute2-6.17.0.tar.xz

sed -i /ARPD/d Makefile
rm -fv man/man8/arpd.8

make NETNS_RUN_DIR=/run/netns

make SBINDIR=/usr/sbin install

install -vDm644 COPYING README* -t /usr/share/doc/iproute2-6.17.0
