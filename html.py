#!/usr/bin/env python3.8
import sys, os

import base64, binascii

out = sys.stdout


def convert_content(basedir, filename, suffix, ctype, fin, fout, out):
    content = fin.read()

    name = filename.rsplit('.', 1)[-2]

    if basedir:
        filename = f"{basedir}/{name}.{suffix}"
    else:
        filename = f"{name}.{suffix}"

    # content = zlib.compress(content, level=9)
    if not ctype in ('text/python', 'sh',):
        content = base64.encodebytes(content).decode('utf-8')


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
                with open(f'{folder}/{filename}', 'rb') as fin:
                    convert_content(target, filename, 'sh', 'sh', fin, fout, out)

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

                    with open(f'{folder}/{filename}', 'rb') as fin:
                        convert_content(target, filename, suffix, ctype, fin, fout, out)

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
{open('inflate.min.js','r').read()}
""",
            file=fout,
        )

    print(
        """


String.prototype.rsplit = function(sep, maxsplit) {
    var split = this.split(sep);
    return maxsplit ? [ split.slice(0, -maxsplit).join(sep) ].concat(split.slice(-maxsplit)) : split;
}

const cwd = window.location.href.rsplit('/',2)[1]
const separator = "/" + cwd + "/"

console.log('Current Working Directory :', cwd )


function merge(blob) {
    const url = URL.createObjectURL(blob);
    const scr = document.createElement('script');
    scr.src = url;
    document.body.appendChild(scr);
    document.body.removeChild(scr);
    URL.revokeObjectURL(url);
}

function b64toBlob(base64Data, contentType) {
    contentType = contentType || '';
    var sliceSize = 1024;
    var byteCharacters = atob(base64Data)
    var bytesLength = byteCharacters.length;
    var slicesCount = Math.ceil(bytesLength / sliceSize);
    var byteArrays = new Array(slicesCount);

    for (var sliceIndex = 0; sliceIndex < slicesCount; ++sliceIndex) {
        var begin = sliceIndex * sliceSize;
        var end = Math.min(begin + sliceSize, bytesLength);

        var bytes = new Array(end - begin);
        for (var offset = begin, i = 0; offset < end; ++i, ++offset) {
            bytes[i] = byteCharacters[offset].charCodeAt(0);
        }
        byteArrays[sliceIndex] = new Uint8Array(bytes)
    }
    return new Blob(byteArrays, { type: contentType });
}

async function fopen(script, nodefer){

    var src = script.src.rsplit(separator,1).pop()

    if (window.location.href.startsWith('http'))
        src = src.split(window.location.host+"/",2).pop()
    else {
        src = src.split( window.location.pathname.rsplit('/',1).shift()+"/", 2).pop()
    }


    console.log(" <<FS>> ",src)


    if (script.type == 'data') {
        console.log('data blob[' +  script.id + '] ', src)
        const blob = b64toBlob(script.text, 'application/binary');
        window.sfs[src] = URL.createObjectURL(blob)
        script.text = ""
        return
    }

    if (script.type == 'wasm') {
        console.log('wasm blob[' +  script.id + '] ', src)
        const blob = b64toBlob(script.text, 'application/wasm');
        window.sfs[src] = URL.createObjectURL(blob)
        script.text = ""
        return
    }

    if (script.type == 'text/python') {
        console.log('python source [' +  script.id + '] ', src)
        console.log("code :", script.text.length)
        return
    }

    if (script.type == 'sh') {
        console.log('shell source [' +  script.id + '] ', script.text)
        window.cmdline = script.text
        return
    }

    if ( (script.type == 'lib') || (script.type == 'js') ) {
        console.log('js found', script.src)
        const blob = b64toBlob(script.text, 'text/javascript');

        if (script.type == 'lib') {
            console.log("decoded module("+script.id+"): ", src )
            const url = URL.createObjectURL(blob);
            ld[script.id] = await import(url)
            window[script.id] = ld[script.id]
            URL.revokeObjectURL(url);
        } else {
            console.log("decoded script("+script.id+"): ", src )
            if ( nodefer ) {
                merge(blob)
            } else {
                console.log("    -> deferred")
            }

        }
        script.text = ""
        return
    }

}

function source(src) {

    for (const script of document.getElementsByTagName('script')) {
        if (script.type == 'js') {
            if (script.src.endsWith(src)) {
                console.log('sourcing', src, 'from', script.src)
                return fopen(script, true)
            }
//else { console.log(src,script.src) }
        }
    }
    console.log("could not source",src)
}

function import_module(alias, src) {
    if (!window.ld[alias] ) {
        console.log("import_module miss", alias, src)
        for (const script of document.getElementsByTagName('script')) {
            if ( (script.type == 'js') && (script.id == alias) )
                console.log("TODO fetch",script.src)
        }
    } else {
        console.log("import_module hit", alias)
    }
    return window.ld[alias]
}

window.ld = {}
window.sfs = {}

window.clog = console.log
window.log = console.log


for (const script of document.getElementsByTagName('script')) {
    // clear text
    if ( (script.type == 'text/python') || (script.type == 'sh') ) {
        fopen(script)
        continue
    }

    // b64, could be compressed
    if ( (script.type == 'data') || (script.type == 'wasm') ){
        fopen(script)
        continue
    }

    // b64 could be compressed, or could be cleartext
    if (script.type == 'lib') {
        fopen(script)
        continue
    }
}


window.offline = function offline() {

    function locateFile(path) {
        var fsn = path.split('.').shift() + "/" + path
        console.log('LOCATING :' , fsn )
        const furl = window.sfs[fsn]
        if (!furl)
            console.log('    Not Found :',path,'from',fsn)
        return furl
    }

    function preInit() {
        console.log(' ========== PRE-INIT ===========')
    }

    window.Module["locateFile"] = locateFile
    window.Module["preInit"] =  preInit

    window.Module["fopen"] =  function (fsn) {
        console.log('LOCATING :', fsn )
        const furl = window.sfs[fsn]
        if (!furl) {
            console.log('    Not Found :', fsn," trying fetch")
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
            console.log('************* found script at " + argstart +" to run from cmdline : ' + elem)
            console.log('sys.argv ', elems)
            break
        }
        console.log(' ****************', elem ,'******************** ')
        vm.argv.push( elems.shift() )
    }
    window.Module.arguments = elems

    source( vm.script.interpreter + "/" + vm.script.interpreter + ".js")
}

source("pythons/main.js")


--></script>""",
        file=fout,
    )

