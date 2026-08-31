#!/bin/bash
# OVERRIDE ch11/01-theend: the release files, saying the true thing — this
# system is tup 0.1, built from LFS arm64-r12.4 by the witnessed pipeline.
set -e
echo "tup 0.1 (built on LFS arm64-r12.4-42)" > /etc/lfs-release
cat > /etc/lsb-release << "LSBEOF"
DISTRIB_ID="tup"
DISTRIB_RELEASE="0.1"
DISTRIB_CODENAME="witness"
DISTRIB_DESCRIPTION="tup 0.1"
LSBEOF
cat > /etc/os-release << "OSEOF"
NAME="tup"
VERSION="0.1 (witness)"
ID=tup
PRETTY_NAME="tup 0.1"
VERSION_CODENAME="witness"
HOME_URL="https://github.com/jonhhjackson-a11y/srlm-forge"
OSEOF
