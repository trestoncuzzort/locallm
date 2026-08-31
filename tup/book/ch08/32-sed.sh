# 8.32. Sed-4.9
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/sed.html
# TUP_PACKAGE=sed-4.9

./configure --prefix=/usr

make
make html

if tup_tests_enabled "sed"; then
chown -R tester .
su tester -c "PATH=$PATH make check"
else tup_receipt_skip_tests "sed"; fi

make install
install -d -m755           /usr/share/doc/sed-4.9
install -m644 doc/sed.html /usr/share/doc/sed-4.9
