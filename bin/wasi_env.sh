
export WASI_SDK_PATH=$(realpath $(dirname "$BASH_SOURCE")/../wasi-sdk)
SYSROOT="--sysroot=$(realpath ${WASI_SDK_PATH}/share/wasi-sysroot) --target=wasm32-unknow-wasi"
FIX="-D__WASI__=1 -include ${WASI_SDK_PATH}/fix.h"


export CC="$(command -v clang) -g0 -Os ${SYSROOT} $FIX"
export CXX="$(command -v clang)++ -g0 -Os ${SYSROOT} $FIX"
export CPP="clang ${SYSROOT} $FIX -E"

echo " wasi sdk set as:
CC=$CC
CXX=$CXX
CPP=$CPP
"






