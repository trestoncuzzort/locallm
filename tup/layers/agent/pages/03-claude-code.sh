# tup layer agent: Claude Code
# TUP_ACTION_PAGE
#
# The point of the layer. Installed from npm, which means tens of thousands of
# files tup did not build and cannot account for the way it accounts for the
# base system. That is the honest cost of an AI distro being useful, and it is
# exactly why this is a LAYER: inventory.sh before and after gives the diff,
# so "here is what installing an AI coding agent added to my operating system"
# is a number rather than a shrug.

npm install -g @anthropic-ai/claude-code
ln -sfv /opt/node-v24.20.0/bin/claude /usr/bin/claude 2>/dev/null || true
echo "claude: $(/usr/bin/claude --version 2>&1 | head -1)"
echo "npm global tree: $(find /opt/node-v24.20.0/lib/node_modules -type f | wc -l) files"
