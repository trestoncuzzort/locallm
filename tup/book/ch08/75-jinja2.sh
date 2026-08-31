# 8.77. Jinja2-3.1.6
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/jinja2.html
# TUP_PACKAGE=jinja2-3.1.6

pip3 wheel -w dist --no-cache-dir --no-build-isolation --no-deps $PWD

pip3 install --no-index --find-links dist Jinja2
