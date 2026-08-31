# 9.9. Creating the /etc/shells File
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter09/etcshells.html
# TUP_ACTION_PAGE

cat > /etc/shells << "EOF"
# Begin /etc/shells

/bin/sh
/bin/bash

# End /etc/shells
EOF
