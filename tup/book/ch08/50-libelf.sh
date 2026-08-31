# 8.50. Libelf from Elfutils-0.193
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/libelf.html
# TUP_ACTION_PAGE

./configure --prefix=/usr        \
            --disable-debuginfod \
            --enable-libdebuginfod=dummy

make

if tup_tests_enabled "libelf"; then
make -k check
else tup_receipt_skip_tests "libelf"; fi

make -C libelf install
install -vm644 config/libelf.pc /usr/lib/pkgconfig
rm /usr/lib/libelf.a
