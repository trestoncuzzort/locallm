# 8.46. Intltool-0.51.0
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/intltool.html
# TUP_PACKAGE=intltool-0.51.0

sed -i 's:\\\${:\\\$\\{:' intltool-update.in

./configure --prefix=/usr

make

if tup_tests_enabled "intltool"; then
make check
else tup_receipt_skip_tests "intltool"; fi

make install
install -v -Dm644 doc/I18N-HOWTO /usr/share/doc/intltool-0.51.0/I18N-HOWTO
