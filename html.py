#!/usr/bin/env python3.8
import sys, os

LZMA = "js/lzmad.min.js"
#LZMA = 0

if LZMA:
    import lzma

import base64, binascii

out = sys.stdout


def convert_content(basedir, filename, suffix, ctype, fin, fout, out, diskfile ):
    global LZMA

    content = fin.read()

    name = filename.rsplit('.', 1)[-2]

    if basedir:
        filename = f"{basedir}/{name}.{suffix}"
    else:
        filename = f"{name}.{suffix}"

    if not ctype in ('text/python', 'sh',):
        if LZMA :#
            if ctype=='wasm':
                content = os.popen(f'base64 {diskfile}| lzma -9 --stdout | base64').read()
            else:
                content = os.popen(f'lzma -3 --stdout {diskfile} | base64').read()
        else:
            content = base64.encodebytes(content).decode('ascii')


    else:
        content = content.decode('utf-8')

    print(
        f"""

<script id={name} src="{filename}" type={ctype}>
{content}</script>

""",
        file=fout,
    )

    print(
        f"""
<script id={name} src="{filename}" type={ctype}>... {len(content)} ...</script>
""",
        file=out,
    )


def html_block(fout, out):
    print(
        """

<body>

<form action="javascript:alert('pouet');">

<hr>
Open browser console (ctrl+shift+i) to see WebAssembly module output. <a href=https://github.com/pmp-p/wapy-pack>Build your own</a>
<hr>

<div id="stdio" tabIndex=1></div><canvas id="canvas"><p>Your browser doesn't support canvas.</p></canvas>
<hr>
</form>

<pre id="log"></pre>
</body>

</html>
""", file=fout)


def css_content(filename, fin, fout):
    print(f"css {filename}\n", file=out)
    print(f"<style>{fin.read()}</style>", file=fout)


AppName = f"{sys.argv[-2]}.html"

print(f'App Name : {AppName}', file=out)

with open(AppName, "w") as fout:

    print("""<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0"></head>""", end='', file=fout)
    if sys.argv[-1].endswith('.py'):

        print(f"""<script id=stdin type=text/python>#{sys.argv[-1]}</script>""")

        with open(sys.argv[-1], 'r') as code:
            print(
                f"""<script id=stdin type="text/python">#<!--{code.read()}
#--></script>
""",
                file=fout,
            )

    for folder in sys.argv[1:]:
        if folder.endswith('.py'):
            continue

        target = folder.rsplit('/',1)[-1]

        for filename in os.listdir(folder):
            if filename.endswith('.sh'):
                diskfile = f'{folder}/{filename}'
                with open(diskfile, 'rb') as fin:
                    convert_content(target, filename, 'sh', 'sh', fin, fout, out, diskfile=diskfile)

    for folder in sys.argv[1:]:

        if folder.endswith('.py'):
            continue

        target = folder.rsplit('/',1)[-1]

        for suffix in ('data', 'wasm', 'js','css'):
            for filename in os.listdir(folder):
                if filename.endswith(f'.{suffix}'):
                    ctype = suffix
                    if suffix == 'css':
                        with open(f'{folder}/{filename}', 'r') as fin:
                            css_content(f'{target}/{filename}', fin,fout)
                        continue

                    if suffix == 'js':
                        if os.path.exists(f'{folder}/{filename[:-len(suffix)]}lib'):
                            print(f'{target}/{filename[:-len(suffix)]}lib')
                            ctype = 'lib'

                    diskfile = f'{folder}/{filename}'
                    with open(diskfile, 'rb') as fin:
                        convert_content(target, filename, suffix, ctype, fin, fout, out, diskfile=diskfile)

    html_block(fout, out)

    print(
        f"""
<script async defer><!--
""",
        file=fout,
    )
    if 0:
        print(
            f"""
{open('lib/inflate.min.js','r').read()}
""",
            file=fout,
        )
    elif LZMA:
        print(
            f"""
{open(f'{LZMA}','r').read()}
""", """

const delay = (ms, fn_solver) => new Promise(resolve => setTimeout(() => resolve(fn_solver()), ms*1000));

function _until(fn_solver){
    return async function fwrapper(){
        var argv = Array.from(arguments)
        function solve_me(){return  fn_solver.apply(window, argv ) }
        while (!await delay(0, solve_me ) )
            {};
    }
}

function dec_full(value) {
    return window.uncompressed !== 0
}
function dec_idle(value) {
    return window.uncompressed === 0
}


async function dec(data, as_raw, hint){
    const was = data.length
    var array8 = new Uint8Array(new ArrayBuffer(data.length));
    var i = 0|0;
    for(i = 0; i < data.length; i++) {
        array8[i] = data.charCodeAt(i);
    }

    await _until(dec_idle)()

    LZMA.decompress(array8, function on_decompress_complete(result) {
        if (!result) {
            clog("FAILED decompression",hint, was)
            window.uncompressed = undefined
        } else {
            clog("uncompressed: " , result.length , "was", was);
            window.uncompressed = result;
        }
    }, function on_decompress_progress_update(percent) {
        // document.title = "Decompressing: " + (percent * 100) + "%";
    },
        as_raw
    )

    await _until(dec_full)(0)
    if (window.uncompressed)
        clog("stat", window.rsr_count, hint ,was,'now', window.uncompressed.length)
    return window.uncompressed
}
""",
            file=fout,
        )

    elif 0:
        print(
            """
async function dec(data){
    clog('fake decomp',data.length)
    return data
}

""",
            file=fout,
        )
    else:
        print('''

 ---- NO DECOMPRESSOR -----

''')


    print(
        """
clog = console.log

String.prototype.rsplit = function(sep, maxsplit) {
    var split = this.split(sep);
    return maxsplit ? [ split.slice(0, -maxsplit).join(sep) ].concat(split.slice(-maxsplit)) : split;
}

const cwd = window.location.href.rsplit('/',2)[1]
const separator = "/" + cwd + "/"

clog('Current Working Directory :', cwd )


function merge(dat) {
    const url = URL.createObjectURL(dat);
    const scr = document.createElement('script');
    scr.src = url;
    document.body.appendChild(scr);
    document.body.removeChild(scr);
    URL.revokeObjectURL(url);
}

let toUtf8Decoder = new TextDecoder( "latin1" );

async function b64toBlob(b64data, contentType, hint) {

    try {
        const sliceSize = 1024;
        var pagedata = atob(b64data)

        contentType = contentType || '';

        var blob = undefined

        if (window.dec) {
            const as_raw = false //(contentType === 'application/wasm')
            window.rsr_count++
            blob =  await dec(pagedata, as_raw, hint+ " " + contentType);
            window.rsr_count--
            window.uncompressed = 0

            if (contentType === 'application/wasm') {
                pagedata = atob(blob)
                blob = undefined
            }
        }

        if (blob) {
            return new Blob([blob], { type: contentType });
        } else {

            blob = pagedata

            var bytesLength = blob.length;
            var slicesCount = Math.ceil(bytesLength / sliceSize);
            var byteArrays = new Array(slicesCount);

            for (var sliceIndex = 0; sliceIndex < slicesCount; ++sliceIndex) {
                var begin = sliceIndex * sliceSize;
                var end = Math.min(begin + sliceSize, bytesLength);

                var bytes = new Array(end - begin);
                for (var offset = begin, i = 0; offset < end; ++i, ++offset) {
                    bytes[i] = blob[offset].charCodeAt(0);
                }
                byteArrays[sliceIndex] = new Uint8Array(bytes)
            }
            return new Blob(byteArrays, { type: contentType });
        }
    } catch (x) {
        clog("unable to decode",hint,contentType,x)
    }
}

async function fopen(script, nodefer){

    var src = script.src.rsplit(separator,1).pop()

    if (window.location.href.startsWith('http'))
        src = src.split(window.location.host+"/",2).pop()
    else {
        src = src.split( window.location.pathname.rsplit('/',1).shift()+"/", 2).pop()
    }


    clog(" <<FS>> ",src)


    if (script.type == 'data') {
        clog('data blob[' +  script.id + '] ', src)
        const blob = await b64toBlob(script.text, 'application/binary', src);
        window.sfs[src] = URL.createObjectURL(blob)
        script.text = ""
        return
    }

    if (script.type == 'wasm') {
        clog('wasm blob[' +  script.id + '] ', src)
        const blob = await b64toBlob( script.text, 'application/wasm', src);
        window.sfs[src] = URL.createObjectURL(blob)
        script.text = ""
        return
    }

    if (script.type == 'text/python') {
        clog('python source [' +  script.id + '] ', src)
        clog("code :", script.text.length)
        return
    }

    if (script.type == 'sh') {
        clog('shell source [' +  script.id + '] ', script.text)
        window.cmdline = script.text
        return
    }

    if ( (script.type == 'lib') || (script.type == 'js') ) {
        clog('js found', script.src)
        const blob = await b64toBlob(script.text, 'text/javascript', src);

        if (script.type == 'lib') {
            clog("decoded module("+script.id+"): ", src )
            const url = URL.createObjectURL(blob);
            ld[script.id] = await import(url)
            window[script.id] = ld[script.id]
            URL.revokeObjectURL(url);
        } else {
            clog("decoded script("+script.id+"): ", src )
            if ( nodefer ) {
                merge(blob)
            } else {
                clog("    -> deferred")
            }

        }
        script.text = ""
        return
    }

}


async function source(src) {
    if (window.rsr_count<0) {
        window.rsr_count = 0
        for (const script of document.getElementsByTagName('script')) {
            // clear text
            if ( (script.type == 'text/python') || (script.type == 'sh') ) {
//await
fopen(script)
                continue
            }

            // b64, could be compressed
            if ( (script.type == 'data') || (script.type == 'wasm') ){
await
fopen(script)
                continue
            }

            // b64 could be compressed, or could be cleartext
            if (script.type == 'lib') {
//await
fopen(script)
                continue
            }
        }
    }

    for (const script of document.getElementsByTagName('script')) {
        if (script.type == 'js') {
            if (script.src.endsWith(src)) {
                clog('sourcing', src, 'from', script.src)
                return await fopen(script, true)
            }
//else { clog(src,script.src) }
        }
    }
    clog("could not source",src)
}


function import_module(alias, src) {
    if (!window.ld[alias] ) {
        clog("import_module miss", alias, src)
        for (const script of document.getElementsByTagName('script')) {
            if ( (script.type == 'js') && (script.id == alias) )
                clog("TODO fetch",script.src)
        }
    } else {
        clog("import_module hit", alias)
    }
    return window.ld[alias]
}

window.uncompressed = 0
window.rsr_count = -1
window.rsr_track = -1
window.ld = {}
window.sfs = {}

window.clog = clog
window.log = clog




window.offline = function offline() {

    function locateFile(path) {
        var fsn = path.split('.').shift() + "/" + path
        clog('LOCATING :' , fsn )
        const furl = window.sfs[fsn]
        if (!furl)
            clog('    Not Found :',path,'from',fsn)
        return furl
    }

    function preInit() {
        clog(' ========== PRE-INIT ===========')
    }

    window.Module["locateFile"] = locateFile
    window.Module["preInit"] =  preInit

    window.Module["fopen"] =  function (fsn) {
        clog('LOCATING :', fsn )
        const furl = window.sfs[fsn]
        if (!furl) {
            clog('    Not Found :', fsn," trying fetch")
            return fsn
        }
        return furl
    }

    var elems = cmdline.trim().split(' ')

    vm.script.interpreter = elems.shift()
    var argstart = 0;

    while (elems.length) {
        const elem = elems[0] ;
        if (elem.endsWith(".py")) {
            clog('************* found script at " + argstart +" to run from cmdline : ' + elem)
            clog('sys.argv ', elems)
            break
        }
        clog(' ****************', elem ,'******************** ')
        vm.argv.push( elems.shift() )
    }
    window.Module.arguments = elems

    source( vm.script.interpreter + "/" + vm.script.interpreter + ".js")
}


source("pythons/main.js")


--></script>""",
        file=fout,
    )

