
export WASI_SDK_PATH=$(realpath $(dirname "$BASH_SOURCE")/../wasi-sdk)
SYSROOT="--sysroot=$(realpath ${WASI_SDK_PATH}/share/wasi-sysroot) -include ${WD}/wasi-sdk/fix.h"


export CC="$(command -v clang) -g0 -Os ${SYSROOT}"
export CPP="clang ${SYSROOT} -E"

echo " wasi sdk set as:
$CC
"






