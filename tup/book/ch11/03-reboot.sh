# 11.3. Rebooting the System
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter11/reboot.html
# TUP_ACTION_PAGE

logout

umount -v $LFS/dev/pts
mountpoint -q $LFS/dev/shm && umount -v $LFS/dev/shm
umount -v $LFS/dev
umount -v $LFS/run
umount -v $LFS/proc
umount -v $LFS/sys

umount -v $LFS/home
umount -v $LFS

umount -v $LFS
