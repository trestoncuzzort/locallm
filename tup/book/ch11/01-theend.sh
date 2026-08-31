# 11.1. The End
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter11/theend.html
# TUP_ACTION_PAGE

echo arm64-r12.4-42 > /etc/lfs-release

cat > /etc/lsb-release << "EOF"
DISTRIB_ID="Linux From Scratch"
DISTRIB_RELEASE="arm64-r12.4-42"
DISTRIB_CODENAME="<your name here>"
DISTRIB_DESCRIPTION="Linux From Scratch"
EOF

cat > /etc/os-release << "EOF"
NAME="Linux From Scratch"
VERSION="arm64-r12.4-42"
ID=lfs
PRETTY_NAME="Linux From Scratch arm64-r12.4-42"
VERSION_CODENAME="<your name here>"
HOME_URL="https://www.linuxfromscratch.org/lfs/"
RELEASE_TYPE="development"
EOF
