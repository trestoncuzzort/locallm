# 8.45. XML::Parser-2.47
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/xml-parser.html
# TUP_ACTION_PAGE

perl Makefile.PL

make

if tup_tests_enabled "xml-parser"; then
make test
else tup_receipt_skip_tests "xml-parser"; fi

make install
