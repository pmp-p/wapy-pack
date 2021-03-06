"use strict";
// alias: vm

function log(msg) {
    const out = document.getElementById('log')
    if (out){
        var lines = out.textContent.split("\n")
        while (lines.length > 4 )
            lines.shift()
        out.textContent = lines.join("\n") + msg + '\n';
    }
}

function clog(msg) {
    try {
        log(msg)
    } catch(x){
        console.log(msg)
    }
}


// this is emscripten glue

function preRun(){
    console.log("preRun: Begin")

    console.log("preRun: End")

}


function write_file(dirname, filename, arraybuffer) {
    FS.createPath('/',dirname,true,true);
    FS.createDataFile(dirname,filename, arraybuffer, true, true);
}

function postRun() {
    console.log("postRun: Begin")
    console.log("postRun: End")
}


function init_repl(){

    console.log("repl: Begin (" + arguments_.length+")")

    if ( aio.plink.shm ) {
        console.log("shared memory ptr was set by wasm module to : " + aio.plink.shm )
        console.log("kbd shared memory port was set by wasm module to : " + aio.plink.io_port_kbd )
    } else {
        console.log("ERROR : shared memory ptr setup from EM_ASM failed")
    }

    console.log("init_repl: shm " + aio.plink.shm+"[" + aio.plink.MAXSIZE + "]")

    // set ready for embedded scripts in page
    window.pyscripts = new Array()

    if (script.main) {
        var argv0 = script.main
        clog("Running with sys.argv[0] = '"+ argv0 + "'")

        window.currentTransferSize = 0
        window.currentTransfer = argv0

        var ab = vm.script.fs_get(argv0,'utf-8')
        if (window.currentTransferSize>=0) {
            FS.createDataFile("/",'main.py', ab, true, true);
            console.log("got main.py [" + ab.length +"]")
            PyRun_VerySimpleFile('main.py')
        } else {

            script.puts("Javascript : error getting main.py from '"+argv0+"'\r\n")
            //TODO: global control var to skip page scripts
        }
    }


    if (script.irq) {
        console.log("allow int for bytecode loop preemption")
        //start repl

        PyRun_SimpleString(`
import embed
import pythons
def VMIF(irq, verbose=0):
    # (dis)allow interrupts to return to host(js) while in python virtual machine

    if irq is True:embed.enable_irq()
    elif irq is False:embed.disable_irq()
    if verbose:
        if embed.FLAGS_IF()<=0:
            print("Warning : interrupt disabled, using micropython VM")
        else:
            print("Warning : interrupt enabled, using WAPY VM")

def STI(verbose=0):
    VMIF(True,verbose)

def CLI(verbose=0):
    VMIF(False,verbose)

STI(1)
`)

    } else {
        console.log("no support for bytecode loop preemption")
    }

    init_repl = undefined
    script.repl_init = undefined

}

function runscripts() {
    var scripts = document.getElementsByTagName('script')

    for(var i = 0; i < scripts.length; i++){
        const scr = scripts[i]

        if(scr.type == vm.script.type){
            if (scr.text) {
                clog("added script of len " + scr.text.length )
                pyscripts.push(scr.text)
            }

        }
    }

    // run scripts or start repl asap
    if (pyscripts.length)
        PyRun_SimpleString()
    else
        console.log("no '" + vm.script.type + "' script tag found")
}



// =========================== REPL shm interface ===============================

function PyRun_VerySimpleFile(filename, ascode) {
    var code =`
try:
    exec( open('` + filename + `', 'r').read(), globals() , globals())
except Exception as e:
    sys.print_exception(e)
`
    if (ascode)
        return code
    pyscripts.push(code)
}

//function prepro(text) {
//    return text
//}

// FIXME: ordering of scripts blocks => use a queue and do it async
function PyRun_SimpleString(text){
    if ( getValue( aio.plink.shm, 'i8') ) {
        console.log("shm locked, retrying in 16 ms")
        setTimeout(PyRun_SimpleString, 16, text )
        return //
    }

    if (!text)
        text = pyscripts.shift()
    if (text) {
        var header = text.substring(0,64).trim()


        // no : for script tags
        var async_script = header.startsWith('#!async')

        //if (async_script)
        //    console.log("==== ASYNC TL =======> "+header)

        // for script file there's :
        header = header.replace('async:','').replace(' ','').trim()

        if ( header.startsWith("#!") ) {
            header = header.split("\n")[0].substr(2).trim()
            // if not .py found then it's a script tag.
            text = PyRun_VerySimpleFile(":"+header, true)
            console.log("====================================")
            console.log(text)
            console.log("====================================")
            /*
            if ( header.endsWith('.py') ) {
                console.log("Getting shebang py=["+header+"] async="+ async_script)
                var tmp = script.fs_get(text, "utf-8")
                if (tmp)
                    text=tmp
            }
            */
        }
    }

    if ( text ) {

        //for temporarily fixes
        // text= prepro(text)

        if (text.length >= aio.plink.MAXSIZE)
            console.log("ERROR: python code ring buffer overrun")

        // TODO: ordering of mixed sync/async toplevels
        if (async_script)
            stringToUTF8( text +"\n#async-tl", aio.plink.shm, aio.plink.MAXSIZE )
        else
            stringToUTF8( text, aio.plink.shm, aio.plink.MAXSIZE )

        console.log("wrote "+text.length+"B to shm")
    } //else
        //console.log("invalid text block [" + text + "]")

    if (pyscripts.length)
        return setTimeout(PyRun_SimpleString, 16 )
}




// this is the closest to a readline interface we can get.
function window_prompt(){
    if (window.stdin.length>0) {
        var str = window.stdin
        window.stdin = ""
        console.log("PROMPT["+str+"]")
        return str
    }
    return null
}

function str2ab(str) {
    var buf = new ArrayBuffer(str.length*2); // 2 bytes for each char
    var bufView = new Uint16Array(buf);
    for (var i=0, strLen=str.length; i < strLen; i++) {
        bufView[i] = str.charCodeAt(i);
    }
    return buf;
}

function stdin_raw(){
    // buffer empty ?
    if (!window.stdin.length)
        return

    if (getValue(aio.plink.io_port_kbd, 'i8')) {
        console.log("kbd port @" +  aio.plink.io_port_kbd + " locked, retrying later")
        return
    }

    const utf8 = unescape(encodeURIComponent(window.stdin)) // + "\r\n"

    // event driven repl consume via kbd port.
    window.stdin = ""

    //console.log("ready to send kbdport@" + aio.plink.io_port_kbd + "["+utf8+"]")

    /// flush whole buffer to shared memory as a null terminated str
    stringToUTF8( utf8, aio.plink.io_port_kbd, aio.plink.MP_IO_SIZE)

    //console.log('FLUSHED')
}

// =================================== STDOUT ==================================

function stdio_process(fd, cc) {
    // TODO: multiple vt fds for pty.js
    if (fd==1)
        script.puts(cc)
}

// TODO: add a dupterm for stderr, and display error in color in xterm if not in stdin_raw mode

// ========================== startup hooks ======================================

function setStatus(args) {
    console.log("setStatus : " + args)
}


function preMainLoop(args) {
    //console.log("preMainLoop(js)"+JSON.stringify(aio.plink.state))
    if (aio.plink.MAXSIZE) {
        stdin_raw()
        //pending io/rpc ?
        aio.plink.io()
    } else {
        //console.log("340:plink not ready")
    }

    if (vm.script.cpython && window.stdin_flush) {
        window.stdin += "\n"
        window.stdin_flush = false;
    }

/* debugging repl
    if (vm.script.cpython && window.stdin.length && window.stdin_flush) {
        const utf8 = unescape(encodeURIComponent(window.stdin))
        FS.writeFile("dev/fd/0", utf8, { flags : "w+" } )
        window.stdin = ""
        window.stdin_flush = false;
    }
*/
    return true
}


function pythons(argc, argv){
    var scripts = document.getElementsByTagName('script')

    for (var i = 0; i < scripts.length; i++) {
        var scr = scripts[i]

        if (scr.type == script_type_python) {
            console.log('requesting script interpreter : ' + script.interpreter )
            var emterpretURL = script.interpreter + ".binary"
            var emterpretXHR = new XMLHttpRequest;
                emterpretXHR.open("GET", emterpretURL, !0),
                emterpretXHR.responseType = "arraybuffer",
                emterpretXHR.onload = function() {
                    if ( (200 === emterpretXHR.status) || (0 === emterpretXHR.status) ) {
                        Module.emterpreterFile = emterpretXHR.response
                        console.log("Using "+ script.interpreter + " VM via asyncify")
                    } else {
console.log("Using " + script.interpreter + " VM synchronously because no " + script.interpreter+".binary => " + emterpretXHR.status )
                    }
                    embed_pythons()
                }
                emterpretXHR.send(null)
            break
        }
    }
}


async function embed(config, noauto) {
    if (!noauto) {
        console.log("loading ["+ script.interpreter + "] flavour")
        include(config['prefix'] + script.interpreter + ".js")
    }
    if (config['runscripts']) {
        await _until(defined)("pyscripts")
        runscripts()
    } else {
        console.log('not running embedded scripts')
    }
}


const script = {
    "argv" : [],
    "stdin" : "",
    "stdin_raw"  : true,
    "stdin_echo" : false,
    "fs_get" : undefined,
    "main" : undefined,
    "interpreter" : "?",
    "type" : "text/python",
    "set_host" : script_set_host,
    "embed" : embed,
    "runscripts": runscripts,
    "init_repl" : init_repl,
    'run_scripts' : true,
    'irq' : true,
    'prefix': '../../',
    "vt" : undefined,
    "vt_helper" : undefined,
    "puts" : undefined,
    "cpython" : undefined,
}


var fsync = undefined // import
var fasync = undefined
var window = undefined

var aio = undefined // import
var posix = undefined //aio.posix
var dom = undefined //aio.dom

var argv = []

function vmrx(event) {
    console.log("net: host <<<>>> vm GOT :", event.data, event.origin)
}

function script_set_host(self, win, api_aio, api_fsync, api_fasync) {
    window = win
    window.clog = clog
    window.script_type_python = "text/python"

    try {
        script.host = window.parent && window.parent.ide
    } catch (DOMException) {
        console.log("426:BLOCKED")
        window.addEventListener("message", vmrx, false);
        window.parent.postMessage("ifup", "*")
        script.host = undefined
    }

    aio = api_aio
    posix = api_aio.posix
    dom = api_aio.dom

    if (api_fsync){
        fsync = api_fsync
        clog("VM.FSYNC: fsync support enabled")
    } else {
        clog("VM.FSYNC: no fsync support")
    }

    // ===================================== STDIN ================================

    // aio.plink.pts hold tty devices descriptors
    window.stdin_array = []

    // the readline emulation buffer ( via prompt() )
    // for non event driven repl ( cpython default )
    if (undef("stdin")) {
        window.stdin = ""
    }
    if (undef("Module")) {
        console.log("-- RUNNING FROM USER DEFINED --")

        window.Module = {
            preRun : [preRun],
            postRun: [postRun],
            setStatus : setStatus,
            preMainLoop : preMainLoop,
            print : api_aio.pts_decode,
            printErr : console.log,
    //        dynamicLibraries : ["libsdl2.so","libwapy.so"],
    //        dynamicLibraries : ["libwapy.so"],
    //        dynamicLibraries : ["libsdl2.so"],
        }
    } else {
        console.log("-- RUNNING FROM EMSCRIPTEN DEFAULTS --")
    }

    // not required anymore
    script.set_host = undefined
    script_set_host = undefined
    window.vm = self

    return window.Module

}




export { argv, window, dom, script, PyRun_SimpleString, pythons, window_prompt, stdio_process, aio, posix, fsync, fasync }
