# 8.66. GRUB-2.12
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/grub.html
# TUP_PACKAGE=grub-2.12

unset {C,CPP,CXX,LD}FLAGS

echo depends bli part_gpt > grub-core/extra_deps.lst

./configure --prefix=/usr     \
            --sysconfdir=/etc \
            --disable-efiemu  \
            --disable-werror

make

make install
mv -v /etc/bash_completion.d/grub /usr/share/bash-completion/completions
