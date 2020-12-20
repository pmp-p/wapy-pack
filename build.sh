#!/bin/bash

URL_WASI="https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-12/wasi-sdk-12.0-linux.tar.gz"
URL_PYCOPY="https://github.com/pfalcon/pycopy-lib.git"
CI=${CI:-false}


export PYTHONDONTWRITEBYTECODE=1
for py in 9 8 7 6
do
    if which python3.${py}
    then
        export PYTHON=python3.${py}
        break
    fi
done
echo Will use python $PYTHON
echo

echo "I will download from

URL_WASI=$URL_WASI
URL_PYCOPY=$URL_PYCOPY

"


if $CI
then
    echo "ok"
else
    echo "press enter to continue"
    read
fi



# requirements

if [ -d pycopy-lib ]
then
    cd pycopy-lib
    git config pull.rebase false
    git pull
    cd ..
else
    git clone $URL_PYCOPY
fi

if [ -d wasi-sdk ]
then
    echo " wasi ok"
else
    wget $URL_WASI
    tar xfz wasi-sdk-12.0-linux.tar.gz && rm wasi-sdk-12.0-linux.tar.gz
    mv wasi-sdk-12.0 wasi-sdk
fi




# packer



mkdir -p rom
$PYTHON rom.py
