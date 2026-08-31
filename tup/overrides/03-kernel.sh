#!/bin/bash
# OVERRIDE ch10/03-kernel: `make menuconfig` is a human at a terminal; this
# override scripts the same decision — defconfig plus the virtio/ext4/vfat
# switches a QEMU-virt guest boots from, forced =y so no initramfs is needed.
# `mount /boot` is dropped (tup keeps /boot on the root filesystem; the ESP
# holds only GRUB). Everything else is the book page, byte for byte.
set -e
make mrproper
make defconfig
for opt in VIRTIO_PCI VIRTIO_BLK VIRTIO_NET VIRTIO_CONSOLE EXT4_FS \
           VFAT_FS NLS_CODEPAGE_437 NLS_ISO8859_1 DEVTMPFS DEVTMPFS_MOUNT; do
  ./scripts/config -e "$opt"
done
make olddefconfig
make
make modules_install
cp -v arch/arm64/boot/vmlinuz.efi /boot/vmlinuz-6.17.3-lfs-arm64-r12.4-42
cp -v System.map /boot/System.map-6.17.3
cp -v .config /boot/config-6.17.3
cp -r Documentation -T /usr/share/doc/linux-6.17.3
install -v -m755 -d /etc/modprobe.d
cat > /etc/modprobe.d/usb.conf << "USBEOF"
# Begin /etc/modprobe.d/usb.conf

install ohci_hcd /sbin/modprobe ehci_hcd ; /sbin/modprobe -i ohci_hcd ; true
install uhci_hcd /sbin/modprobe ehci_hcd ; /sbin/modprobe -i uhci_hcd ; true

# End /etc/modprobe.d/usb.conf
USBEOF
