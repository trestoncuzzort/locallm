# 10.4. Using GRUB to Set Up the Boot Process
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter10/grub.html
# TUP_ACTION_PAGE

fdisk -l | grep 'EFI System'

mkdir -pv /boot/efi
mount /boot/efi

grub-install --removable

cat > /boot/grub/grub.cfg << "EOF"
# Begin /boot/grub/grub.cfg
set default=0
set timeout=5

insmod part_gpt
insmod ext2
set root=(hd0,2)

insmod efi_gop

menuentry "GNU/Linux, Linux 6.17.3-lfs-arm64-r12.4-42" {
        linux   /boot/vmlinuz-6.17.3-lfs-arm64-r12.4-42 root=/dev/sda2 ro
}
EOF
