# 7.13. Cleaning up and Saving the Temporary System
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter07/cleanup.html
# TUP_ACTION_PAGE

rm -rf /usr/share/{info,man,doc}/*

find /usr/{lib,libexec} -name \*.la -delete

rm -rf /tools

exit

mountpoint -q $LFS/dev/shm && umount $LFS/dev/shm
umount $LFS/dev/pts
umount $LFS/{sys,proc,run,dev}

cd $LFS
tar -cJpf $HOME/lfs-temp-tools-arm64-r12.4-42.tar.xz .
