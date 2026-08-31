# 8.3. Man-pages-6.15
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/man-pages.html
# TUP_PACKAGE=man-pages-6.15

rm -v man3/crypt*

make -R GIT=false prefix=/usr install
