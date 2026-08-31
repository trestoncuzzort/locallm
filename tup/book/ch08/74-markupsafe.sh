# 8.76. MarkupSafe-3.0.3
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/markupsafe.html
# TUP_PACKAGE=markupsafe-3.0.3

pip3 wheel -w dist --no-cache-dir --no-build-isolation --no-deps $PWD

pip3 install --no-index --find-links dist Markupsafe
