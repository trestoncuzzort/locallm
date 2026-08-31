# 7.7. Gettext-0.26
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter07/gettext.html
# TUP_PACKAGE=gettext-0.26

./configure --disable-shared

make

cp -v gettext-tools/src/{msgfmt,msgmerge,xgettext} /usr/bin
