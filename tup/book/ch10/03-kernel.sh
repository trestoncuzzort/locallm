# 10.3. Linux-6.17.3
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter10/kernel.html
# TUP_TARBALL=linux-6.17.3.tar.xz

make mrproper

make menuconfig

make

make modules_install

mount /boot

cp -iv arch/arm64/boot/vmlinuz.efi /boot/vmlinuz-6.17.3-lfs-arm64-r12.4-42

cp -iv System.map /boot/System.map-6.17.3

cp -iv .config /boot/config-6.17.3

cp -r Documentation -T /usr/share/doc/linux-6.17.3

install -v -m755 -d /etc/modprobe.d
cat > /etc/modprobe.d/usb.conf << "EOF"
# Begin /etc/modprobe.d/usb.conf

install ohci_hcd /sbin/modprobe ehci_hcd ; /sbin/modprobe -i ohci_hcd ; true
install uhci_hcd /sbin/modprobe ehci_hcd ; /sbin/modprobe -i uhci_hcd ; true

# End /etc/modprobe.d/usb.conf
EOF
