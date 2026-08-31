# 8.36. Grep-3.12
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/grep.html
# TUP_PACKAGE=grep-3.12

sed -i "s/echo/#echo/" src/egrep.sh

./configure --prefix=/usr

make

if tup_tests_enabled "grep"; then
make check
else tup_receipt_skip_tests "grep"; fi

make install
