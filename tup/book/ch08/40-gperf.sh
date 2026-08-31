# 8.40. Gperf-3.3
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/gperf.html
# TUP_TARBALL=gperf-3.3.tar.gz

./configure --prefix=/usr --docdir=/usr/share/doc/gperf-3.3

make

if tup_tests_enabled "gperf"; then
make check
else tup_receipt_skip_tests "gperf"; fi

make install
