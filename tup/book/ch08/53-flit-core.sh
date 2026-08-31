# 8.54. Flit-Core-3.12.0
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/flit-core.html
# TUP_PACKAGE=flit-core-3.12.0

pip3 wheel -w dist --no-cache-dir --no-build-isolation --no-deps $PWD

pip3 install --no-index --find-links dist flit_core
