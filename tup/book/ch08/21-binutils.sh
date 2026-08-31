# 8.21. Binutils-2.45
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/binutils.html
# TUP_PACKAGE=binutils-2.45

mkdir -v build
cd       build

../configure --prefix=/usr       \
             --sysconfdir=/etc   \
             --enable-ld=default \
             --enable-plugins    \
             --enable-shared     \
             --disable-werror    \
             --enable-64-bit-bfd \
             --enable-new-dtags  \
             --with-system-zlib  \
             --enable-default-hash-style=gnu

make tooldir=/usr

if tup_tests_enabled "binutils"; then
make -k check
else tup_receipt_skip_tests "binutils"; fi

grep '^FAIL:' $(find -name '*.log')

make tooldir=/usr install

rm -rfv /usr/lib/lib{bfd,ctf,ctf-nobfd,gprofng,opcodes,sframe}.a \
        /usr/share/doc/gprofng/
