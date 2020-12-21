"use strict";

/*
function unhex_utf8(s) {
    var ary = []
    for ( var i=0; i<s.length; i+=2 ) {
        ary.push( parseInt(s.substr(i,2),16) )
    }
    return new TextDecoder().decode( new Uint8Array(ary) )
}

function demux_fd(text) {
    try {
        var jsdata = JSON.parse(text);
        for (const key in jsdata) {
            // TODO: multiple vt fds for pty.js
            if (key=="1") {
                var str = unhex_utf8( jsdata[key])
                vm.script.vt.write( str.replace(/\n/g,"\r\n") )
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
        console.log(x,text)
        if (text.length) {
            clog("C-OUT ["+text+"]")
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
*/


let start;
function halted(msg) {
    if (msg) {
        console.log(msg)
        msg = "("+msg+")"
    } else
        msg =""
    vm.script.vt.write(msg + "\r\n\x1b[31m" + "\r\n- system halted -\r\n" + "\x1b[0m " )
}

async function frame(timestamp) {
    if (start === undefined)
        start = timestamp;

    const elapsed = timestamp - start;

    try {
        await Module.aio_suspend()
        Module.dlsym("_start")()
    } catch (x) {
        halted(x)
        return
    }
    window.requestAnimationFrame(frame);
/*
    if (elapsed < 2000) { // Stop the animation after 2 seconds
        window.requestAnimationFrame(frame);
    } else {
        halted('timeout')
    }
*/
}



async function Py_NewInterpreter() {
    const wasm = await import_module("wasm","assets/wasm.js")
    Module.io = wasm.stdio() //{}
    Module.env = {}

    Module.renderpass = 0
/*
    fd 1   : stdout
    fd 2   : stderr
    fd 3   : js-eval / async-rpc
    fd 4   : wasi env
    fd 5   : future use : syscalls / eval

*/

    // { key = value }\n
    Module.io["4"] = function (str){

        for (var text of str.split("\n")) {
            if (!text.length)
                continue

            for (const [key, value] of Object.entries( JSON.parse(text) )) {
                if ( Array.isArray(value) ) {
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
                    const slot = ViewSlots[value[0]]
                    value.push( "set" + slot )
                    value.push( "get" + slot )
                }
                console.log("KV:",key,value)
                Module.env[key] = value

            }
        }
    }

    Module.io["5"] = function (str){
        try {
            var argv = JSON.parse(str)
            console.log("syscall", argv )
        } catch(x) {
            console.log("syscall N/I:", str )
        }
    }


    Module.stdio = function stdio_custom(fd, str){
        //console.log("["+fd+"]",str)
        const channel = Module.io[fd]
        if (channel)
            Module.io[fd](str)
        else
            console.log("I/O on closed fd :",fd)
    }

    Module.aio_suspend = async function aio_suspend() {
        if (window.stdin) {
            Module.dlo.poke_utf8(Module.env.io_port_kbd - Module.env.shm, window.stdin, Module.env.MP_IO_SIZE)
            window.stdin = ""
        }
    }

    Module.dlsym = null
    Module.name = "wapy"
    Module.path = "wapy/wapy.wasm"

    Module.dlo = await wasm.dlopen(Module);

    Module.dlsym("_start")()

    window.requestAnimationFrame(frame)

    var scripturl = window.location.hash.substr(1)
    if (scripturl) {
        scripturl = "https://wyz.fr/paste" + scripturl.split('wyz.fr',2)[1]

        const original = scripturl

        scripturl = "https://cors-anywhere.herokuapp.com/" + scripturl +"/raw"
        //console.log( scripturl )
        fetch(scripturl)
            .then(response => response.text())
            .then((response) => {
                console.log("GOT SCRIPT:",response) //.length)
                vm.script.vt.write("\r\nInspecting __main__ from '"+ original +"'\r\n")
                Module.dlo.poke_utf8(0, response +"#\n", Module.env.MP_IO_SIZE)
        }).catch(err => console.log("failed script:", scripturl, err))


    } else {
        if (Module.arguments.length) {
            var data = Module.fopen(Module.arguments[0])
            if ( data == Module.arguments[0] ) {
                data = document.getElementById("stdin").text
                document.getElementById("stdin").text = ""
            }
            console.log('>>>>> Module argv',Module.arguments, data)
            Module.dlo.poke_utf8(0, data +"#\n", Module.env.MP_IO_SIZE)
        }
    }

// http://127.0.0.1:8000/wasi/app_wapy.html?wapy&-i&-u&-B#https://wyz.fr/3G-BS

}




Py_NewInterpreter()

