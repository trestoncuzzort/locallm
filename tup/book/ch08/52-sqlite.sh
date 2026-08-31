# 8.52. Sqlite-3500400
# https://www.linuxfromscratch.org/~xry111/lfs/view/arm64/chapter08/sqlite.html
# TUP_TARBALL=sqlite-autoconf-3500400.tar.gz

tar -xf ../sqlite-doc-3500400.tar.xz

./configure --prefix=/usr    \
            --disable-static  \
            --enable-fts{4,5} \
            CPPFLAGS="-D SQLITE_ENABLE_COLUMN_METADATA=1 \
                      -D SQLITE_ENABLE_UNLOCK_NOTIFY=1   \
                      -D SQLITE_ENABLE_DBSTAT_VTAB=1     \
                      -D SQLITE_SECURE_DELETE=1"

make LDFLAGS.rpath=""

make install

install -v -m755 -d /usr/share/doc/sqlite-3.50.4
cp -v -R sqlite-doc-3500400/* /usr/share/doc/sqlite-3.50.4
