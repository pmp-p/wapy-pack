import sys
import builtins

sys.modules['builtins'] = builtins
sys.modules['sys'] = sys
sys.modules['__main__'] = __import__('__main__')

meta_path = []
zipimports = []


# try to fix vars
try:
    vars
except:
    try:
        import embed
        builtins.vars = embed.builtins_vars
        sys.modules['embed'] = embed
    except:
        print("WARNING: that Python implementation lacks vars()", file=sys.stderr)

try:
    import posix
except:
    import os as posix

import types

if hasattr(types,"ModuleType__call__"):
    print("25:#FIXME: types.ModuleType(modulename) call")
    tmcall = types.ModuleType__call__
else:
    tmcall = types.ModuleType

# keep the builtin function accessible in this module and via imp.__import__
__import__ = builtins.__import__

mpath = []

# Deprecated since version 3.4: Use types.ModuleType instead.
# but micropython aims toward full 3.4

# Return a new empty module object called name. This object is not inserted in sys.modules.
def new_module(name):
    global tmcall
    return tmcall(name)

if sys.platform in ("asm.js", "wasm", "wasi"):
    def parser(path_url):
        global __import__
        return open(path_url).read()
else:
    def parser(path_url):
        global __import__
        return posix.popen('future-fstrings-show "{}"'.format(path_url) ).read()


def importer(name, *argv, **kw):
    global __import__, mpath

    reparse = None

    # check lvl  eg for __import__('__main__') => len(argv) == 0

    #print("60:",name)

    if len(argv)!=4:
        if name in sys.modules:
            return sys.modules[name]
        raise ImportError('ImporterParentError(%s)' % name)

    mod = None

    glob, loc, froml, lvl = argv




    if not lvl:
        mpath.append(name)
        dotpath = mpath[-(lvl+1):]
    else:
        dotpath = mpath[-(lvl):]
        dotpath.append(name)




    name = '.'.join(dotpath).strip('.')
    #print("imp :",dotpath,' => ', name, glob, loc, froml, lvl , kw, )

    if name in sys.modules:
        mod = sys.modules[name]
    else:
        print("imp :",dotpath,' => ', name, glob, loc, froml, lvl , kw, )
        try:
            mod = __import__(name, glob, loc, froml, 0)
        except ValueError as e:
            print("93:    ValueError",name,e)
        except SyntaxError as e:
            reparse  = sys.modules[name].__file__
            print("96:    reparse: Module '{}' from '{}' ".format(name,reparse))
        except ImportError as e:
            print("98:    ",e)

    if mod is not None:
        if not lvl:
            mpath.pop()
        return mod

#    module was not loaded, so now options are :
#        - we had a file that need special parsing.
#        - a file that may be online
#        - a file stored in some archive

    if reparse:
        filen = reparse
        code = parser(reparse)
    else:
        filen = ':{0}.py'.format(name)
        print("INFO: getting online or archive local version of", filen, file=sys.stderr)

        try:
            code = open(filen, 'r').read()
        except Exception as e:
            print('127:imp :',e)
            remote = False
            for i, path_url in enumerate(sys.path):
                if path_url.startswith('http://') or path_url.startswith('https://'):
                    filen = '{0}/{1}.py'.format(path_url, name)
                    print("INFO: try to get online remote version of", filen, file=sys.stderr)
                    try:
                        code = open(filen, 'r').read()
                        remote = True
                        break
                    except:
                        continue

                # minimal zipimport, TODO relative imports
                data = b''
                zfn = ''
                for zf in zipimports:
                    zfn = zf.filename().decode('utf-8')
                    if path_url.startswith(zfn):
                        inzip_path = path_url[len(zfn):].lstrip('/.')

                        for test in (name , '%s/__init__' % name, '%s/%s' % (name,name) ):
                            filen = '{}/{}.py'.format( inzip_path, test )
                            zf.open(filen)
                            data = zf.read()
                            if data:
                                print('tested',filen, len(data))
                                break
                        if data:
                            break
                if data:
                    code = data.decode('utf-8')
                    filen = '%s/%s' % ( zfn, filen )
                    break
            else:
                raise ImportError('module "{}" not found'.format(name))

    # build a empty module
    mod = new_module(name)

    mod.__file__ = filen

    # compile module from cached file
    try:
        code = compile(code, filen, 'exec')
    except Exception as e:
        print('140:imp :',e)
        sys.print_exception(e)
        raise

    # micropython would insert module before executing the whole body
    # and left it that way even on runtime error.
    sys.modules[name] = mod

    # execute it in its own empty namespace.
    try:
        ns = vars(mod)
    except:
        print("WARNING: that Python implementation lacks vars()", file=sys.stderr)
        ns = mod.__dict__

    try:
        exec(code, ns, ns)
    except Exception as e:
        print('158:imp :',e)
        sys.print_exception(e)
        #
        # do not follow weird micropython behaviour and clean up zombie module
        del sys.modules[name]
        mpath.pop()
        raise

    if not lvl:
        path = mpath.pop()
        # TODO: check package modules
        # register module as a symbol in its "parent"
        if path.find('.')>0:
            pname, anchor = path.rsplit('.',1)
            vars(  sys.modules.get( pname ) )[anchor] = mod
    return mod


builtins.__import__ = importer

