import sys
import builtins


def byte(char):
    return bytes( (char.encode()[0],) )

builtins.byte = byte


# get  the real importer in case we are late fixing
# or fallback to builtins
impattr = getattr( sys.modules.get('imp', __import__('builtins') ), '__import__' ,  __import__ )


def fixme(name):
    global impattr
    fix = '%s.%s' % ( __name__ , name )
    impattr( fix )
    #module = eval(module)
    module = sys.modules.get(fix)
    module.__file__ = '<fixes>'
    module.__name__ = name
    sys.modules[name] = module
    del sys.modules[fix]

    # todo maybe upgrade existing modules namespaces
    #setattr( builtins, module.__name__, module )
    return module

# running micropython ~3.4
if __UPY__: # or sys.version_info[:2]<(3,7):

    #builtins.__UPY__ = True

    #important for __import__( . ) in fixme
    import pythons

    if sys.platform == 'wasm':
        fixes = ('struct', 'ctypes','utime')
    else:
        #order matters
        fixes = ('micropython','machine', 'struct', 'ctypes', 'contextlib','contextvars', 'utime')

else:
    # running cpython
    builtins.__UPY__ = False

    import traceback

    if not hasattr(sys,"print_exception"):
        def print_exception(e, out=sys.stderr, **kw):
            kw["file"] = out
            traceback.print_exc(**kw)

        sys.print_exception = print_exception

    import pythons
    import pythons.fixes as fixes
    pythons.fixes = fixes
    sys.modules['time'] = fixme('utime')
    print(utime, sys.modules['utime'])

    #contextvars is unsupported on micropython

    if __WASM__:
        fixes = ('micropython', 'machine', 'signal')
    elif hasattr(sys, "getandroidapilevel"):
        fixes = ('micropython', 'machine')
    else:
        #fixes = ('micropython', 'machine', 'ctypes')
        fixes = ('micropython', 'machine')


for fix in fixes:
    try:
        fixme(fix)
        print('58:FIXED :',fix)
    except Exception as e:
        print("59:fix",fix,"failed :", e)
        sys.print_exception(e)

if __UPY__:
    import uarray
    sys.modules['array'] = uarray

    import uos
    sys.modules['os'] = uos

    import ujson
    sys.modules['json'] = ujson

    import uio
    sys.modules['io'] = uio

    import ubinascii
    sys.modules['binascii'] = ubinascii

    import utime
    sys.modules['time'] = utime
