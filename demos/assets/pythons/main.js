"use strict";
// alias: main

function log(msg) {
    const out = document.getElementById('log')
    if (out){
        var lines = out.textContent.split("\n")
        while (lines.length > 4 )
            lines.shift()
        out.textContent = lines.join("\n") + msg + '\n';
    }
    return out
}

function clog(msg) {
    if (!log(msg))
        console.log(msg)
}

window.clog = clog
window.log = log


if (!window.undef) {

    function undef(e,o){
        if (typeof o === 'undefined' || o === null)
            o = window;

        try {
            e = o[e];
        } catch (x) { return true }

        if (typeof e === 'undefined' || e === null)
            return true;
        return false;
    }

    function defined(e,o){return !undef(e,o)}

    const delay = (ms, fn_solver) => new Promise(resolve => setTimeout(() => resolve(fn_solver()), ms*1000));

    String.prototype.rsplit = function(sep, maxsplit) {
        var split = this.split(sep);
        return maxsplit ? [ split.slice(0, -maxsplit).join(sep) ].concat(split.slice(-maxsplit)) : split;
    }

    function trim(str) {
        var str = str.replace(/^\s\s*/, ''),
            ws = /\s/,
            i = str.length;
        while (ws.test(str.charAt(--i)));
        return str.slice(0, i + 1);
    }


    function register(fn,fn_dn){
        if ( undef(fn_dn) )
            fn_dn = fn.name;
        //console.log('  |-- added ' + fn_dn );
        window[fn_dn]=fn;
    }

    //cyclic dep
    window.register = register

    register(undef)
    register(defined)

    function include(filename, filetype){
        var fileref = undefined

        if (filename){

            if (filetype===null ||typeof filetype === 'undefined')
                filetype = 'js';
                if (filename.endsWith('css'))
                    filetype = 'css';

            if ( (filename.indexOf('.') === 0) || (filename.indexOf('/') === 0 ) ){
                //absolute local server
            } else {
                if (filename.startsWith('http://') || filename.startsWith('https://')) {
                //absolute remote
                } else {
                    //corrected
                    filename = (window.JSDIR || '') + filename;
                }
            }
        }

        if (filetype=="js"){ //if filename is a external JavaScript file
            fileref=document.createElement('script')
            fileref.setAttribute("type","text/javascript")
            fileref.setAttribute("src", filename)
            fileref.setAttribute('async',false);
            fileref.setAttribute('onerror','alert("Not found : ' + filename + '")' )
        }
        else if (filetype=="css"){ //if filename is an external CSS file
            fileref=document.createElement("link")
            fileref.setAttribute("rel", "stylesheet")
            fileref.setAttribute("type", "text/css")
            fileref.setAttribute("href", filename)
        }   else {
            console.log("#error can't include "+filename+' as ' +filetype);
            return false;
        }
        // .py includes ??

        console.log("#included "+filename+' as ' +filetype);
        document.getElementsByTagName("head")[0].appendChild(fileref)
        fileref.async = false;
        fileref.defer = false;
    }
    register(include)

    function _until(fn_solver){
        return async function fwrapper(){
            var argv = Array.from(arguments)
            function solve_me(){return  fn_solver.apply(window, argv ) }
            while (!await delay(0, solve_me ) )
                {};
        }
    }
    register(_until)

}


var fsync
var aio
var vm
var vt


async function window_load(event) {

    fsync = await import_module("fsync", "pythons/fsync.js")

    aio = await import_module("aio", "pythons/aio.js")

    vm = await import_module("vm", "pythons/vm.js")

    // it includes the clear screen helper even for xterm.js
    // so always load it
    vt = await import_module("vt","pythons/vt.js")

    // set a default CORS handler asap
    if (!aio.posix.cors) {
        vm.script.prefix="./"

        aio.posix.cors_broker = "https://cors-anywhere.herokuapp.com/"
        aio.posix.cors = function (url){
                if (url.includes('/wyz.fr/'))
                    return aio.posix.cors_broker + url
                return url
        }
        console.log("Using default brooker vm.aio.posix.cors_broker = " + aio.posix.cors_broker)
    }


    // bad sync file getter for poc
    vm.script.fs_exists = fsync.wasm_file_exists

    // FIXME:
    vm.script.fs_get = fsync.awfull_get

    Module = vm.script.set_host(vm, window, aio, fsync, undefined)

    // pseudo-readline buffer toward Python wasm vm via emscripten stdio polyfill
    window.prompt = vm.window_prompt

    console.log('VM.STARTUP :  The page is fully loaded : ' + window.location);

    var found = false

    if (!window.offline) {
        for (const script of document.getElementsByTagName('script')) {
            if (script.type == 'module') {
                if ( (script.src.search('#')>0) && ( script.src.search('pythons/main.js') >0) ) {
                    var elems = script.src.rsplit('#',1)
                    var url = elems.shift()
                    var code = elems.shift()

                    elems = url.rsplit('?',1)
                    url = elems.shift()

                    elems = elems.shift().split('&')
                    vm.script.interpreter = elems.shift()

                    Array.prototype.push.apply(vm.argv, elems )
                    console.log('script: interpreter=' + vm.script.interpreter)
                    console.log('script: url='+url)


                    console.log(script.src)
                    console.log('code : '+code)
                    vm.script.main = code
                    found = true
    // TODO scripts argv ( sys.argv )
                }
            }
        }
    } else {
        console.log('205:========================================')
        window.offline()
        console.log('206:========================================')
    }

    if (!found) {
        clog("ERROR", window.location.href )
    }

    if (vm.script.interpreter.startsWith("python")) {
        console.log("VM.irq : no preemption (cpython)")
        vm.script.irq = false
        window.stdin_flush = false
    } else {
        vm.script.cpython = false
    }

    console.log('VM.argv : '+JSON.stringify(vm.argv))

/*
TODO:
    -x     : skip first line of source, allowing use of non-Unix forms of #!cmd
    -q     : don't print version and copyright messages on interactive startup
    -m mod : run library module as a script or apk (terminates option list)
*/

    if (vm.argv.includes("-u"))
        clog('VM: -u raw tty requested')

    if (vm.argv.includes("-B")) {
        clog('VM: -B do not store compiled bytecode')
    }

    vm.script.trace = function trace(ln) {
        if (vm.script.host) {
            setTimeout(() => window.parent.ide.setCursor(0+ln,0), 1)
        }
    }

    if (vm.script.host) {
        clog("VM.SCRIPT: trace enabled")
        if (window.feed) {
            try {
                window.feed.innerHTML = "❯❯❯"
            } catch (x) {}
        }
        window.parent.vm = vm
    } else {
        clog("VM.script: trace disabled")
    }

    clog("// TODO: extract vm.script.argv not interpreter")
    /* we still can modify argc/argv.
    var argv = window.location.href.split('?',2)
    var e;
    while (e=argv.shift())
        arguments_.push(e)
    argv = arguments_.pop().split('&')
    while (e=argv.shift())
        arguments_.push(e)
    */
    if ( defined('PYTHONSTARTUP') ){
        await PYTHONSTARTUP()
    }

    // do not override user defined terminal if it was set
    if (!vm.script.puts) {

        // -i means interactive : we *need* a terminal use simpleterm as fallback.
        if (vm.argv.includes("-i")) {
            if (!window.terminal) {
                vm.script.vt = new vt.Terminal("#stdio", 120, 29)
                vm.script.vt.open()
            } else {
                clog("VM.script.vt : assuming xterm.js instance in window.vt")
                vm.script.vt = window.terminal
            }

            vm.script.vt.on('key', vt.handlevt)

            vm.script.puts = function(text){
                vm.script.vt.write(text)
            }

            clog('VM: terminal requested ' + vm.script.vt)

        } else {
            /* Write text to dom instead of user supplied terminal */
            document.body.setAttribute('style', 'white-space: pre;');

            vm.script.puts = function(text){ document.body.innerHTML += text }
        }
    }

    // default term helper
    if (!vm.script.vt_helper) {
        vm.script.vt_helper = vt.helper
    }
    vm.script.embed( vm.script, window.offline )

}



if (!window.offline) {
    window.ld = {}
    window.import_module = async function import_module(alias, src) {
        if (!window.ld[alias] ) {
            console.log('import',"../../assets/" + src)
            window.ld[alias] = await import( "../../assets/" + src )
        }
        return window.ld[alias]
    }
}

// fix for demo
if (window.vm && window.vm.script && !window.vm.script.set_host) {
        window.parent.device.open('vide.html','device')
} else {
    let navData = window.performance.getEntriesByType("navigation");

    if (navData.length > 0 && navData[0].loadEventEnd > 0)
    {
        console.log('Document is already loaded, starting module manually');
        setTimeout(window_load,0)
    } else {
        console.log('Document is not loaded, queuing to load event');
        window.addEventListener('load', window_load )
    }
}





















//
