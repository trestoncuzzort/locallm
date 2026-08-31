# 7.12. Util-linux-2.41.2
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter07/util-linux.html
# TUP_TARBALL=util-linux-2.41.2.tar.xz

mkdir -pv /var/lib/hwclock

./configure --libdir=/usr/lib     \
            --runstatedir=/run    \
            --disable-chfn-chsh   \
            --disable-login       \
            --disable-nologin     \
            --disable-su          \
            --disable-setpriv     \
            --disable-runuser     \
            --disable-pylibmount  \
            --disable-static      \
            --disable-liblastlog2 \
            --without-python      \
            ADJTIME_PATH=/var/lib/hwclock/adjtime \
            --docdir=/usr/share/doc/util-linux-2.41.2

make

make install
