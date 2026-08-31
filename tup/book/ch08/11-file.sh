# 8.11. File-5.46
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/file.html
# TUP_PACKAGE=file-5.46

./configure --prefix=/usr

make

if tup_tests_enabled "file"; then
make check
else tup_receipt_skip_tests "file"; fi

make install
