# 8.57. Setuptools-80.9.0
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/setuptools.html
# TUP_PACKAGE=setuptools-80.9.0

pip3 wheel -w dist --no-cache-dir --no-build-isolation --no-deps $PWD

pip3 install --no-index --find-links dist setuptools
