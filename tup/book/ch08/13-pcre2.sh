# 8.13. Pcre2-10.46
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/pcre2.html
# TUP_TARBALL=pcre2-10.46.tar.bz2

./configure --prefix=/usr                       \
            --docdir=/usr/share/doc/pcre2-10.46 \
            --enable-unicode                    \
            --enable-jit                        \
            --enable-pcre2-16                   \
            --enable-pcre2-32                   \
            --enable-pcre2grep-libz             \
            --enable-pcre2grep-libbz2           \
            --enable-pcre2test-libreadline      \
            --disable-static

make

if tup_tests_enabled "pcre2"; then
make check
else tup_receipt_skip_tests "pcre2"; fi

make install
