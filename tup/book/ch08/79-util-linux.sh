# 8.81. Util-linux-2.41.2
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/util-linux.html
# TUP_PACKAGE=util-linux-2.41.2

./configure --bindir=/usr/bin     \
            --libdir=/usr/lib     \
            --runstatedir=/run    \
            --sbindir=/usr/sbin   \
            --disable-chfn-chsh   \
            --disable-login       \
            --disable-nologin     \
            --disable-su          \
            --disable-setpriv     \
            --disable-runuser     \
            --disable-pylibmount  \
            --disable-liblastlog2 \
            --disable-static      \
            --without-python      \
            --without-systemd     \
            --without-systemdsystemunitdir        \
            ADJTIME_PATH=/var/lib/hwclock/adjtime \
            --docdir=/usr/share/doc/util-linux-2.41.2

make

bash tests/run.sh --srcdir=$PWD --builddir=$PWD

if tup_tests_enabled "util-linux"; then
touch /etc/fstab
chown -R tester .
su tester -c "make -k check"
else tup_receipt_skip_tests "util-linux"; fi

make install
