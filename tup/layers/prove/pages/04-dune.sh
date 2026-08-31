# prove 4: dune 3.16.1 — Rocq's build system, bootstrapped by ocaml itself.
# TUP_TARBALL=dune-3.16.1.tar.gz
make release
make install PREFIX=/usr
dune --version
