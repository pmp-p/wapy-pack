#!/bin/bash

# https://coderwall.com/p/r09hoq/android-generate-release-debug-keystores

# keytool -genkey -v -keystore debug.keystore -storepass android -alias androiddebugkey -keypass android 
#  -keyalg RSA -keysize 2048 -validity 10000

# keytool -list -v -keystore [keystore path] -alias [alias-name] -storepass [storepass] -keypass [keypass] 
# keytool -list -v -keystore debug.keystore -alias androiddebugkey -storepass android -keypass android 

KEYSTORE=${1:-debug.keystore}
OUT=$(basename $KEYSTORE .keystore)
echo "

KEYSTORE=$KEYSTORE
OUT=$OUT
"
read

#/opt/sdk/jdk1.8.0_192/bin/
keytool -importkeystore -srckeystore ${KEYSTORE} -destkeystore $OUT.p12 -deststoretype PKCS12
openssl pkcs12 -in $OUT.p12 -nokeys -out $OUT.cert.pem
openssl pkcs12 -in $OUT.p12  -nodes -nocerts -out $OUT.key.pem
