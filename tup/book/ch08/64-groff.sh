# 8.65. Groff-1.23.0
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/groff.html
# TUP_PACKAGE=groff-1.23.0

PAGE=<paper_size> ./configure --prefix=/usr

make

if tup_tests_enabled "groff"; then
make check
else tup_receipt_skip_tests "groff"; fi

make install
