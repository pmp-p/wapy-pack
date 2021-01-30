"use strict";

// WASI POLYFILL for WAPY

const wlog = console.log

const nav_start_ns = performance.timing.navigationStart * 1_000_000

const ViewSlots = {
    u8 : "Uint8",
    u16 : "Uint16",
    u32 : "Uint32",
    u64 : "BigUint64",
    i8 : "Int8",
    i16 : "Int16",
    i32 : "Int32",
    i64 : "BigInt64",
}

var io_buffers = {}
var io_channel = 1

var WASI = function(iomapper) {

    var table = null;

    const WASI_ESUCCESS = 0;
    const WASI_EBADF = 8;
    const WASI_EINVAL = 28;
    const WASI_ENOSYS = 52;


    function stubber(name) {
        return function stub(){console.log('stub',name,arguments)}
    }


    /// We call gsync any time the guest's memory may have changed,
    /// such as when creating a new instance, or after calling _malloc.

    function peek(addr) {
        const view = gsync();
        return view.getUint8(Module.env.shm + addr)
    }


    function poke(addr,B) {
        var view = gsync();
        view.setUint8(Module.env.shm + addr, B & 0xff)
    }


    function peek_32(addr) {
        const view = gsync();
        return view.getUint32(Module.env.shm + addr)
    }


    function poke_32(addr,B) {
        var view = gsync();
        view.setUint32(Module.env.shm + addr, B & 0xff)
    }


// FIXME: maxsize check
    function poke_utf8(offset, s, maxsize) {
        var view = gsync();
        var addr = Module.env.shm + offset
        //const end = start + s.length
        for ( var i=0; i<s.length; i++) {
            view.setUint8(addr++, s.charCodeAt(i))
        }
    }


    function gsync() {
        // call this any time you'll be reading or writing to a module's memory
        // the returned DataView tends to be dissaociated with the module's memory buffer at the will of the WebAssembly engine
        // cache the returned DataView at your own peril!!
        const mbuf = table.memory.buffer;
        return new DataView(mbuf);
    }



    function dlopen(Module) {
        table = Module.vm.exports
        Module.dlsym = function dlsym(entry) {
            const sym = table[entry]
            if (!sym)
                console.log("dl:",Module.name, ": symbol '" + entry + "' not found" )
            return sym
        }
    }

    // =======================================================================================================
    // poke*
/*
    function memset(key, v) {
        const slot = Module.env[key]
        if (slot) {
            var view = gsync();
            const writer = "set" + ViewSlots[slot[0]]
            const reader = "get" + ViewSlots[slot[0]]

            view[writer](slot[1], v, !0 )
            console.log(key, "@"+slot[1],v , view[reader](slot[1], !0) )
        }
    }
*/
    function memset(key, v) {
        const slot = Module.env[key]
        if (slot) {
            var view = gsync();
            view[slot[2]](slot[1], v, !0 )
            //wlog(key, "@"+slot[1], v, view[slot[3]](slot[1], !0) )
        }
    }

    // hack for 64bits signatures of some critical calls.
    function sched_yield() {
        const env = Module.env

        if (env.tsec){
            const now = ( nav_start_ns + (performance.now() * 1_000_000) ).toFixed(0)

            const tsec = (now / 1_000_000_000).toFixed(0)
            const tsec_ns = tsec * 1_000_000_000

            const usec = ( (now - tsec_ns ) / 1_000 ).toFixed(0)

            const nsec = (now - tsec_ns).toFixed(0)

            //console.log(' NS=',now)
            //console.log("T tsec,usec,nsec :",tsec,usec,nsec)

            memset("tsec",  tsec )
            memset("tusec", usec )
            memset("tnsec", nsec )

            //var view = gsync();
            //view.setUint32( Module.env.tnsec[1], 450320000)

        }
        return 0;
    }


    // =======================================================================================================

    function fd_prestat_get(fd, bufPtr) {

        return WASI_EBADF;
    }

    function fd_prestat_dir_name(fd, pathPtr, pathLen) {

         return WASI_EINVAL;
    }

    function environ_sizes_get(environCount, environBufSize) {

        var view = gsync();

        //wlog("environ_sizes_get",environCount, environBufSize)

        view.setUint32(environCount, 0, !0);
        view.setUint32(environBufSize, 0, !0);

        return WASI_ESUCCESS;
    }

    function environ_get(environ, environBuf) {
        //wlog("environ_get",environ, environBuf)
        return WASI_ESUCCESS;
    }

    function args_sizes_get(argc, argvBufSize) {
        //wlog("args_sizes_get",argc, argvBufSize)
        var view = gsync();

        view.setUint32(argc, 0, !0);
        view.setUint32(argvBufSize, 0, !0);

        return WASI_ESUCCESS;
    }

    function args_get(argv, argvBuf) {
        //wlog("args_get",argv, argvBuf)
        return WASI_ESUCCESS;
    }



    function fd_fdstat_get(fd, bufPtr) {

        var view = gsync();

        view.setUint8(bufPtr, fd);
        view.setUint16(bufPtr + 2, 0, !0);
        view.setUint16(bufPtr + 4, 0, !0);

        function setBigUint64(byteOffset, value, littleEndian) {

            var lowWord = value;
            var highWord = 0;

            view.setUint32(littleEndian ? 0 : 4, lowWord, littleEndian);
            view.setUint32(littleEndian ? 4 : 0, highWord, littleEndian);
       }

        setBigUint64(bufPtr + 8, 0, !0);
        setBigUint64(bufPtr + 8 + 8, 0, !0);

        return WASI_ESUCCESS;
    }

    function getiovs(view, iovs, iovs_len) {
        // iovs* -> [iov, iov, ...]
        // __wasi_ciovec_t {
        //   void* buf,
        //   size_t buf_len,
        // }
        var buffers = Array.from({ length: iovs_len }, function (_, i) {
               var ptr = iovs + i * 8;
               var buf = view.getUint32(ptr, !0);
               var bufLen = view.getUint32(ptr + 4, !0);

               return new Uint8Array(table.memory.buffer, buf, bufLen);
            });

        return buffers;
    }

    function fd_write(fd, iovs, iovs_len, nwritten) {

        var view = gsync();

        var written = 0;
        var bufferBytes = [];

        var buffers = getiovs(view, iovs, iovs_len);

        function writev(iov) {

            for (var b = 0; b < iov.byteLength; b++) {

               bufferBytes.push(iov[b]);
            }

            written += b;
        }

        buffers.forEach(writev);

        iomapper(fd, String.fromCharCode.apply(null, bufferBytes));

        view.setUint32(nwritten, written, !0);

        return WASI_ESUCCESS;
    }

    function poll_oneoff(sin, sout, nsubscriptions, nevents) {

        return WASI_ENOSYS;
    }

    function proc_exit(rval) {

        return WASI_ENOSYS;
    }

    function fd_close(fd) {

        return WASI_ENOSYS;
    }

    function fd_seek(fd, offset, whence, newOffsetPtr) {

    }

    function fd_read(fd, iovs, iovs_len, nread) {
        console.log("fd_read", fd, iovs, iovs_len, nread)
        return WASI_EBADF;
    }



    return {
        dlopen : dlopen,

        environ_sizes_get : environ_sizes_get,
        args_sizes_get : args_sizes_get,
        fd_prestat_get : fd_prestat_get,
        fd_fdstat_get : fd_fdstat_get,
        fd_write : fd_write,
        fd_prestat_dir_name : fd_prestat_dir_name,
        environ_get : environ_get,
        args_get : args_get,
        poll_oneoff : poll_oneoff,
        proc_exit : proc_exit,
        fd_close : fd_close,
        fd_seek : fd_seek,
        fd_read : fd_read,

        peek : peek,
        poke : poke,
        poke_utf8 : poke_utf8,

        memset : memset,
        sched_yield : sched_yield,

        fd_readdir : stubber("fd_readdir"),
        clock_time_get : stubber("clock_time_get"),
        gettimeofday : stubber("gettimeofday"),
        fd_sync : stubber("fd_sync"),

        path_open : stubber("path_open"),
        path_filestat_get : stubber("path_filestat_get"),
        path_unlink_file : stubber("path_unlink_file"),
        path_create_directory : stubber("path_create_directory"),
        fd_fdstat_set_flags : stubber("fd_fdstat_set_flags"),
    }
}

export async function dlopen(Module) {
    const url = Module.fopen(Module.path)
    const as_bc = fetch(url)

    const wasi = new WASI(Module.stdio || console.log);
    const memory = new WebAssembly.Memory({ initial: 128, maximum: 4096 });

    //const moduleImports = { wasi_unstable: wasi, args : Module.argv, env : Module.env, js: { mem: memory } };
    const moduleImports = { wasi_snapshot_preview1: wasi, args : Module.argv, env : Module.env, js: { mem: memory } };

    if (WebAssembly.instantiateStreaming) {
        wlog("WebAssembly.instantiateStreaming")
        const result = await WebAssembly.instantiateStreaming(as_bc, moduleImports);
        Module.wasm = result.module
        Module.vm = result.instance

    } else {
        if (WebAssembly.compileStreaming) {
            wlog("WebAssembly.compileStreaming")
            Module.wasm = await WebAssembly.compileStreaming(as_bc)
        } else {
            wlog("fallback compile/instantiate")
            const response = await as_bc
            const ab = await response.arrayBuffer()
            Module.wasm = await WebAssembly.compile(ab)
        }
        Module.vm = await WebAssembly.instantiate(Module.wasm, moduleImports);
    }

    URL.revokeObjectURL(url)

    wasi.dlopen(Module)

    return wasi
}


function unhex_utf8(s) {
    var ary = []
    for ( var i=0; i<s.length; i+=2 ) {
        ary.push( parseInt(s.substr(i,2),16) )
    }
    return new TextDecoder().decode( new Uint8Array(ary) )
}


//        io_buffers[io_channel] = (io_buffers[io_channel] or "") + stream

function demux_fd(text) {

    try {
        var jsdata = JSON.parse(text);
        for (const key in jsdata) {
            // TODO: multiple vt fds for pty.js
            if (key=="1") {
                var str = unhex_utf8( jsdata[key])
                window.vm.script.vt.write( str.replace(/\n/g,"\r\n") )
                continue
            }
            try {
                embed_call(jsdata[key])
            } catch (e) {
                clog("IOEror : "+e)
            }
        }
    } catch (x) {
        // found a raw C string via libc
        console.log("394",x,text)
        if (text.length) {
            clog("C-OUT ["+text+"]")
        }
    }
}

function io_hex(textblob) {

    try {
        for (var stream of textblob.split("\n")) {
            if (stream.length>0) {
                if (stream.charAt(0) == '@') {
                    const splitter = stream.search(':')
                    io_channel = stream.substr(1, splitter-1)
                    stream = stream.substr(splitter+1)

                }
                window.vm.script.vt.write( unhex_utf8(stream).replace(/\n/g,"\r\n") )
            }
        }
    } catch (x) {
        // found a raw C string via libc
        console.log("418",x,textblob)
        if (textblob.length) {
            clog("C-OUT ["+textblob+"]")
        }
    }

}


// this is a the demultiplexer for stdout and os (DOM/js/aio ...) control
function pts_decode(textblob){
    for (var text of textblob.split("\n")) {
        if (text.length>0)
            demux_fd(text)
    }
}

export function stdio() {
    var io = {}
    io["1"] = function (str) {
        window.vm.script.vt.write(str.replace(/\n/g,"\r\n") )
    }

    io["2"] = function (str) {
        vm.script.vt.write("\x1b[31m" + str.replace(/\n/g,"\r\n") + "\x1b[0m" )
    }

    io["3"] = function (str) {
        console.log("IOHEX")
        io_hex(str)
    }

    io["6"] = function (str) {
        str = str.replace(/\r\n$/g,"").replace(/\n$/g,"")
        if (str)
            console.log(str);
    }

    return io
}

