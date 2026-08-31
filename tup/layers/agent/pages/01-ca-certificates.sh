# tup layer agent: CA certificates
# TUP_ACTION_PAGE
#
# Without a trust store every HTTPS connection fails, so this is the first
# thing the layer needs and the reason it comes before Node. tup takes the
# Mozilla CA bundle as curl.se publishes it, rather than building make-ca and
# p11-kit, and RECORDS THAT CHOICE: this is trust imported wholesale from
# Mozilla's program, not trust derived on this machine. The hash of the exact
# bundle installed is written beside it so a later reader can tell which set
# of roots this system was trusting.

install -vdm755 /etc/ssl/certs
install -vm644 /sources/cacert.pem /etc/ssl/certs/ca-bundle.crt
ln -sfv /etc/ssl/certs/ca-bundle.crt /etc/ssl/cert.pem
sha256sum /etc/ssl/certs/ca-bundle.crt > /etc/ssl/certs/ca-bundle.crt.sha256
cat >> /etc/profile << "EOF"
export SSL_CERT_FILE=/etc/ssl/certs/ca-bundle.crt
export NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-bundle.crt
EOF
echo "CA roots installed: $(grep -c 'BEGIN CERTIFICATE' /etc/ssl/certs/ca-bundle.crt) certificates"
