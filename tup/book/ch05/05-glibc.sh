# 5.5. Glibc-2.42
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter05/glibc.html
# TUP_TARBALL=glibc-2.42.tar.xz

patch -Np1 -i ../glibc-2.42-fhs-1.patch

mkdir -v build
cd       build

echo "rootsbindir=/usr/sbin" > configparms

../configure                             \
      --prefix=/usr                      \
      --host=$LFS_TGT                    \
      --build=$(../scripts/config.guess) \
      --disable-nscd                     \
      libc_cv_slibdir=/usr/lib           \
      --enable-kernel=5.4

make

make DESTDIR=$LFS install

sed '/RTLDLIST=/s@/usr@@g' -i $LFS/usr/bin/ldd

echo 'int main(){}' | $LFS_TGT-gcc -x c - -v -Wl,--verbose &> dummy.log
readelf -l a.out | grep ': /lib'

grep -E -o "$LFS/lib.*/S?crt[1in].*succeeded" dummy.log   || true   # advisory: see extract_book.py

grep -B3 "^ $LFS/usr/include" dummy.log   || true   # advisory: see extract_book.py

grep 'SEARCH.*/usr/lib' dummy.log |sed 's|; |\n|g'   || true   # advisory: see extract_book.py

grep "/lib.*/libc.so.6 " dummy.log   || true   # advisory: see extract_book.py

grep found dummy.log   || true   # advisory: see extract_book.py

rm -v a.out dummy.log
