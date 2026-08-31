# 8.56. Wheel-0.46.1
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/wheel.html
# TUP_PACKAGE=wheel-0.46.1

pip3 wheel -w dist --no-cache-dir --no-build-isolation --no-deps $PWD

pip3 install --no-index --find-links dist wheel
