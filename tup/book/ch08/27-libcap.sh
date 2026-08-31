# 8.27. Libcap-2.76
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/libcap.html
# TUP_PACKAGE=libcap-2.76

sed -i '/install -m.*STA/d' libcap/Makefile

make prefix=/usr lib=lib

if tup_tests_enabled "libcap"; then
make test
else tup_receipt_skip_tests "libcap"; fi

make prefix=/usr lib=lib install
