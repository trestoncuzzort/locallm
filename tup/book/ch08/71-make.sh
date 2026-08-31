# 8.71. Make-4.4.1
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/make.html
# TUP_TARBALL=make-4.4.1.tar.gz

./configure --prefix=/usr

make

if tup_tests_enabled "make"; then
chown -R tester .
su tester -c "PATH=$PATH make check"
else tup_receipt_skip_tests "make"; fi

make install
