# prove 6: Rocq 9.2.0 FROM SOURCE. tup compiles its own proof kernel.
# TUP_TARBALL=rocq-9.2.0.tar.gz
./configure -prefix /usr
make dunestrap
dune build -p rocq-runtime,rocq-core,coq-core,coqide-server -j $(nproc) 2>/dev/null \
  || make -j$(nproc) world
make install || dune install -p rocq-runtime,rocq-core,coq-core --prefix /usr
coqc --version || rocq --version
