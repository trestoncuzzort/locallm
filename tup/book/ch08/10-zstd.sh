# 8.10. Zstd-1.5.7
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/zstd.html
# TUP_PACKAGE=zstd-1.5.7

make prefix=/usr

if tup_tests_enabled "zstd"; then
make check
else tup_receipt_skip_tests "zstd"; fi

make prefix=/usr install

rm -v /usr/lib/libzstd.a
