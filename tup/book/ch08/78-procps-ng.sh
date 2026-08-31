# 8.80. Procps-ng-4.0.5
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/procps-ng.html
# TUP_PACKAGE=procps-ng-4.0.5

./configure --prefix=/usr                           \
            --docdir=/usr/share/doc/procps-ng-4.0.5 \
            --disable-static                        \
            --disable-kill                          \
            --enable-watch8bit

make

if tup_tests_enabled "procps-ng"; then
chown -R tester .
su tester -c "PATH=$PATH make check"
else tup_receipt_skip_tests "procps-ng"; fi

make install
