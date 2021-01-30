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
    echo " * skipping externals repo disclaimer"
else
    echo "
I will download from :

URL_WAPY=$URL_WAPY
URL_WASI=$URL_WASI
URL_PYCOPY=$URL_PYCOPY
URL_PYBPC=$URL_PYBPC

Press enter to continue if you agree.
"
    read
fi



# requirements
# -----------------------------------------


# micropython/pycopy/wapy standard library

if [ -d pycopy-lib ]
then
    cd pycopy-lib
    git pull --ff-only
    cd ..
else
    git clone $URL_PYCOPY
fi


# f2format  f-strings transpiler

$PYTHON -m install --user --upgrade git+$URL_PYBPC.git


# latest WASI sdk

if [ -d wasi-sdk ]
then
    echo "
    * wasi sdk found
"
else
    # remove failed downloads if any
    rm wasi-sdk-*-linux.tar.gz
    wget $URL_WASI
    tar xfz wasi-sdk-*-linux.tar.gz && rm wasi-sdk-*-linux.tar.gz && mv wasi-sdk-* wasi-sdk
fi


# wapy mod source

if [ -d wapy ]
then
    if [ -f localdev ]
    then
        . localdev
    else
        cd wapy
        git pull --ff-only
        cd ..
    fi
else
    git clone -b wapy-wasi $URL_WAPY
fi



# workaround wasi-js limitations
# -----------------------------------------
if [ -f wasi-sdk/fix.h ]
then
    echo "
    * wasi64->wasi32 browser patch already applied
"
else
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
fi


# ~~build native tools~~ wasi sdk clang can do it
# CC=clang make -C wapy/mpy-cross



# packer
# -----------------------------------------


mkdir -p rom
$PYTHON rom.py


export PATH=${WD}/bin:${WD}/wapy/mpy-cross:${WD}/wasi-sdk/bin:$PATH

rm wapy/ports/wapy-wasi/wapy/wapy.wasm

export USER_C_MODULES=${WD}/wapy/ports/wapy/cmod/wasi

# build native tools with wasi sdk clang
CC=clang make -C wapy/mpy-cross


if PYTHONPATH=./wapy-lib $PYTHON -u -B -m modgen
then
    echo "

    * transpiled cmod from $USER_C_MODULES
"
else
    echo "ERROR: modgen failed to transpile C modules from $USER_C_MODULES"
    exit 1
fi

export FIX="-include $(realpath wasi-sdk/fix.h)"
. bin/wasi_env.sh


if make -C wapy/ports/wapy-wasi \
 CC="$CC" CPP="$CPP" NO_NLR=1 \
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

