
export WASI_SDK_PATH=$(realpath $(dirname "$BASH_SOURCE")/../wasi-sdk)
SYSROOT="--sysroot=$(realpath ${WASI_SDK_PATH}/share/wasi-sysroot) --target=wasm32-unknown-wasi"
FIX="-D__WASI__=1 $FIX"


export CC="${WASI_SDK_PATH}/bin/clang -g0 -Os ${SYSROOT} $FIX"
export CXX="${WASI_SDK_PATH}/bin/clang++ -g0 -Os ${SYSROOT} $FIX"
export CPP="${WASI_SDK_PATH}/bin/clang ${SYSROOT} $FIX -E"

echo " wasi sdk set as:
CC=$CC
CXX=$CXX
CPP=$CPP
"






