# 5.4. Linux-6.17.3 API Headers
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter05/linux-headers.html
# TUP_ACTION_PAGE

make mrproper

make headers
find usr/include -type f ! -name '*.h' -delete
cp -rv usr/include $LFS/usr
