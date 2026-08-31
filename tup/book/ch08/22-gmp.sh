# 8.22. GMP-6.3.0
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/gmp.html
# TUP_PACKAGE=gmp-6.3.0

sed -i '/long long t1;/,+1s/()/(...)/' configure

./configure --prefix=/usr    \
            --enable-cxx     \
            --disable-static \
            --docdir=/usr/share/doc/gmp-6.3.0

make
make html

if tup_tests_enabled "gmp"; then
make check 2>&1 | tee gmp-check-log
else tup_receipt_skip_tests "gmp"; fi

awk '/# PASS:/{total+=$3} ; END{print total}' gmp-check-log

make install
make install-html
