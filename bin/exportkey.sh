#!/bin/bash
KEYSTORE=${1:-debug.keystore}
OUT=$(basename $KEYSTORE .keystore)
echo "

KEYSTORE=$KEYSTORE
OUT=$OUT
"
read
/opt/sdk/jdk1.8.0_192/bin/keytool -importkeystore -srckeystore ${KEYSTORE} -destkeystore $OUT.p12 -deststoretype PKCS12
openssl pkcs12 -in $OUT.p12 -nokeys -out $OUT.cert.pem
openssl pkcs12 -in $OUT.p12  -nodes -nocerts -out $OUT.key.pem
