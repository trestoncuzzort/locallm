# 8.59. Meson-1.9.1
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/meson.html
# TUP_TARBALL=meson-1.9.1.tar.gz

pip3 wheel -w dist --no-cache-dir --no-build-isolation --no-deps $PWD

pip3 install --no-index --find-links dist meson
install -vDm644 data/shell-completions/bash/meson /usr/share/bash-completion/completions/meson
install -vDm644 data/shell-completions/zsh/_meson /usr/share/zsh/site-functions/_meson
