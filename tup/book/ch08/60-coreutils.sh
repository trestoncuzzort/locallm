# 8.61. Coreutils-9.8
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/coreutils.html
# TUP_PACKAGE=coreutils-9.8

patch -Np1 -i ../coreutils-9.8-i18n-2.patch

autoreconf -fv
automake -af
FORCE_UNSAFE_CONFIGURE=1 ./configure \
            --prefix=/usr            \
            --enable-no-install-program=kill,uptime

make

make NON_ROOT_USERNAME=tester check-root

groupadd -g 102 dummy -U tester

chown -R tester .

su tester -c "PATH=$PATH make -k RUN_EXPENSIVE_TESTS=yes check" \
   < /dev/null

groupdel dummy

make install

mv -v /usr/bin/chroot /usr/sbin
mv -v /usr/share/man/man1/chroot.1 /usr/share/man/man8/chroot.8
sed -i 's/"1"/"8"/' /usr/share/man/man8/chroot.8
