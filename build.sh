#!/bin/bash

URL_WASI="https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-12/wasi-sdk-12.0-linux.tar.gz"
URL_PYCOPY="https://github.com/pfalcon/pycopy-lib.git"
URL_WAPY="https://github.com/pmp-p/wapy.git"
URL_PYBPC="https://github.com/pybpc/f2format"
CI=${CI:-false}

WD=$(pwd)


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



if $CI
then
    echo "skip disclaimer"
else
    echo "
I will download from :

URL_WASI=$URL_WASI
URL_PYCOPY=$URL_PYCOPY
URL_WAPY=$URL_WAPY
URL_PYBPC=$URL_PYBPC

press enter to continue.
"
    read
fi



# requirements
# -----------------------------------------

if [ -d pycopy-lib ]
then
    cd pycopy-lib
    git pull --ff-only
    cd ..
else
    git clone $URL_PYCOPY
fi

if [ -d wasi-sdk ]
then
    echo " * wasi ok"
else
    wget $URL_WASI
    tar xfz wasi-sdk-12.0-linux.tar.gz && rm wasi-sdk-12.0-linux.tar.gz
    mv wasi-sdk-12.0 wasi-sdk
fi

if [ -d wapy ]
then
    cd wapy
    git pull --ff-only
    cd ..
else
    git clone -b wapy-wasi $URL_WAPY
fi

$PYTHON -m install --user --upgrade git+$URL_PYBPC.git


# patches
# -----------------------------------------

cat > wasi-sdk/fix.h <<END_WASI_SDK_FIX
#include <time.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>


extern struct timeval wa_tv;
extern unsigned int wa_ts_nsec;

static int wasi_clock_gettime(clockid_t clockid, struct timespec *ts) {
    sched_yield();
    ts->tv_sec = wa_tv.tv_sec;
    ts->tv_nsec = wa_ts_nsec;
    return 0;
}


static int wasi_gettimeofday(struct timeval *tv) {
    sched_yield();
    tv->tv_sec = wa_tv.tv_sec;
    tv->tv_usec = wa_tv.tv_usec;
    return 0;
}


#undef clock_gettime
#undef gettimeofday

#define wa_clock_gettime(clockid, timespec) wasi_clock_gettime(clockid, timespec)
#define wa_gettimeofday(timeval, tmz) wasi_gettimeofday(timeval)
END_WASI_SDK_FIX











# packer
# -----------------------------------------

export PATH=${WD}/bin:${WD}/wapy/mpy-cross:${WD}/wasi-sdk/bin:$PATH


mkdir -p rom
$PYTHON rom.py

CC=clang make -C wapy/mpy-cross

rm wapy/ports/wapy-wasi/wapy/wapy.wasm

USER_C_MODULES=${WD}/wapy/ports/wapy/cmod/wasi



if PYTHONPATH=./wapy-lib $PYTHON -u -B -m modgen
then
    echo " * transpiled cmod ok"
else
    echo "ERROR: modgen failed to transpile C modules from $USER_C_MODULES"
    exit 1
fi


CC="clang --sysroot=${WD}/wasi-sdk/share/wasi-sysroot -include ${WD}/wasi-sdk/fix.h"



if make -C wapy/ports/wapy-wasi \
 CC="$CC" NO_NLR=1 \
 CFLAGS_EXTRA="-DMODULE_EMBED_ENABLED=1 -DMODULE_EXAMPLE_ENABLED=1 -DMODULE__ZIPFILE_ENABLED=1"\
 USER_C_MODULES=${USER_C_MODULES} \
 FROZEN_MPY_DIR=${WD}/rom \
 FROZEN_DIR=${WD}/wapy/ports/wapy/flash \
 CWARN="-Wall" USER_C_MODULES=$USER_C_MODULES "$@"
then
    echo "============== build success, creating demo ========="
    mkdir -p build
    mv wapy/ports/wapy-wasi/wapy.wasm demos/wapy/
    $PYTHON html.py demos/assets/pythons demos/wasi demos/wapy demos/app_wapy demos/app_wapy/main.py
    echo "HtmlApp built"
    du -hs demos/app_wapy.html
else
    rm demos/app_wapy.html
fi


































#

