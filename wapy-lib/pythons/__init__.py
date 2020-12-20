# ❯❯❯

# opiniated decision to make sys/time/aio available everywhere to reduce scripting bloat / repl overhead
# if you don't agree, continue to write all your imports as usual :)

# carefull order matters a lot in this file


import sys
import builtins

builtins.sys = sys
builtins.builtins = builtins

builtins.LOGS = []


def pdb(*argv, **kw):
    kw["file"] = sys.stderr
    print("\033[31mPYDEBUG>\033[0m ", *argv, **kw)


#
# def log_reduce(argv,**kw):
#    max = kw.pop('limit',35)
#    lim = (max - 5) // 2
#    for arg in argv:
#        arg = str(arg)
#        if lim and len(arg)>max:
#            arg = "%s/.../%s" % ( arg[:lim] , arg[-lim:] )
#
#        print(arg,end=' ',file=sys.stderr)
#    print('',file=sys.stderr)
#
# def pdb(*argv,**kw):
#    sys.stdout.flush()
#    sys.stderr.flush()
#    if not isinstance(argv[0],str):
#        argv=list(argv)
#        print('[ %s ]' % argv.pop(0), end=' ', file=sys.stderr)
#
#    try:
#        if argv[0].find('%')>=0:
#            try:
#                print(argv[0] % tuple(argv[1:]),file=sys.stderr)
#            except:
#                log_reduce(argv,**kw)
#    except:
#        log_reduce(argv,**kw)
#
#    finally:
#        sys.stdout.flush()
#        sys.stderr.flush()

builtins.pdb = pdb


# those  __dunder__ are usually the same used in C conventions.

try:
    __UPY__
except:
    builtins.__UPY__ = hasattr(sys.implementation, "mpy")

try:
    __EMSCRIPTEN__
except:
    builtins.__EMSCRIPTEN__ = sys.platform in ("emscripten", "asm.js", "wasm", "wasi")

try:
    __WASM__
except:
    builtins.__WASM__ = sys.platform in ("wasm", "wasi")

try:
    __ANDROID__
except:
    # this *is* the cpython way
    builtins.__ANDROID__ = hasattr(sys, "getandroidapilevel")


# this should be done in site.py / main.c but that's not so easy for cpython.
# last chance to do it since required by aio.*
try:
    undefined
except:

    class sentinel:
        def __bool__(self):
            return False

        def __repr__(self):
            return "∅"

        def __nonzero__(self):
            return 0

        def __call__(self, *argv, **kw):
            if len(argv) and argv[0] is self:
                return True
            print("Null Pointer Exception")

    sentinel = sentinel()
    builtins.undefined = sentinel
    del sentinel


def overloaded(i, *attrs):
    for attr in attrs:
        if attr in i.__class__.__dict__:
            if attr in i.__dict__:
                return True
    return False


builtins.overloaded = overloaded


# force use a fixed, tested version of uasyncio to avoid non-determinism
if __UPY__:
    sys.modules["sys"] = sys
    sys.modules["builtins"] = builtins
    try:
        from . import uasyncio as uasyncio
        print('Warning : using WAPY uasyncio')
    except Exception as e:
        sys.print_exception(e)

else:
    # fix const without writing const in that .py because of micropython parser.
    exec("__import__('builtins').const = lambda x:x", globals(), globals())
    from . import uasyncio_cpy as uasyncio

sys.modules["uasyncio"] = uasyncio


# check for embedding support or use an emulation from host script __main__ .

try:
    import embed
except:
    print("WARNING: embed module not found, using __main__ for it", file=sys.stderr)
    embed = __import__("__main__")

try:
    embed.log
except:
    pdb("CRITICAL: embed functions not found in __main__")
    embed.enable_irq = print
    embed.disable_irq = print
    embed.log = print

try:
    embed.select
except:
    pdb("no embed.select")
    try:
        import select
        embed.select = select.select
    except:
        pass


try:
    embed.demux_fd
except:
    pdb("no embed.demux_fd")
    try:
        def demux_fd(fd, data):
            sys.__stdout__.write(data)
        # won't pass on upy
        embed.demux_fd = demux_fd
    except:
        pass

try:
    embed.stdio_append
except:
    pdb("no embed.stdio_append")
    try:
        def stdio_append(fd, data):
            aio.fd[0]

        embed.stdio_append = stdio_append
    except:
        pass

try:
    embed.prompt_request
except:
    pdb("no embed._prompt_request")
    try:
        embed._prompt_request = 0

        def prompt_request():
            embed._prompt_request = 1

        embed.prompt_request = prompt_request
    except:
        pass


sys.modules["embed"] = embed


print(
    "platform: {} {} {} {}".format(
        '__UPY__={!r}'.format(__UPY__),
        '__EMSCRIPTEN__={!r}'.format(__EMSCRIPTEN__),
        '__ANDROID__={!r}'.format(__ANDROID__),
        '__WASM__={!r}'.format(__WASM__),
    )
)


# import possible fixes leveraging various python implementations.

from . import fixes


# aio is a vital component make sure it is wide access.
try:
    import pythons.aio
    from .python3 import *
    # order last : this is expected to be a patched module
    import time
    builtins.time = time
except Exception as e:
    if __UPY__:
        sys.print_exception(e)
    else:
        raise


# allows to call from C, pyv(elem) adds elements to call stack
# eg from main.c:
#    pyv( mp_obj_get_type(ex) );
#    pyv( MP_OBJ_FROM_PTR(ex) );
#    pyv( MP_ROM_NONE );
#    mp_obj_t result = pycore("pyc_excepthook");
#

print('++++++++++++++')

pyc_jump = {"": undefined}


def pycore(fn):
    global pyc_jump
    pyc_jump[fn.__name__] = fn


builtins.pycore = pycore


if __UPY__:
    import io

    sys.modules["io"] = io

    core_argv = []
    core_kw = {}

    format_list = []

    def __excepthook__(type, exc, tb, **kw):
        format_list = kw.get("format_list", [])
        fn = kw.get("file")
        ln = kw.get("line")

        print(end='\r')
        print("_" * 45)
        print("Traceback, most recent call : %s:%s" % (fn, ln))
        while len(format_list):
            print(format_list.pop(0), end="")
        print("_" * 45)

    excepthook = __excepthook__

    @pycore
    def pyc_test(*argv, **kw):
        print("pyc_test (pythons.__init__:103):")
        print("argv : ", argv)
        print("kw : ", kw)
        print("done")

    # should be set only interactive mode and moved into traceback module
    #    last_type = None
    #    last_value = None
    #    last_traceback = None

    @pycore
    def pyc_excepthook(etype, exc, tb, **kw):
        # https://docs.python.org/3.8/library/traceback.html
        #        last_value = exc
        #        last_type = etype
        try:
            # FIXME: extracting that way may trips on inlined '\n'
            # ideally: make a list from C in "tb"
            buf = io.StringIO()
            sys.print_exception(exc, buf)
            buf.seek(0)
            fn = "<stdin>"
            ln = 1
            for line in buf.read().split("\n"):
                ls = line.strip()
                if not ls.startswith("Traceback "):
                    format_list.append(line + "\r\n")
                if ls and ls.startswith('File "'):
                    try:
                        fn, ln = ls.split('", line ', 1)
                        ln = int(ln.split(",", 1)[0])
                        fn = fn[7:-1]
                    except:
                        fn = "<stdin>"
                        ln = 1
            excepthook(etype, exc, tb, file=fn, line=ln, format_list=format_list)

        except Exception as e:
            print("_" * 45)
            sys.print_exception(exc)
            print()
            print("Got another exception while printing exception:")
            print("_" * 45)
            sys.print_exception(e)
            print("_" * 45)
        finally:
            format_list.clear()

    # TODO check "undefined" from C to allow a default C handler to be used
    # when function is not found in jump table

    def core_py(fn):
        global pyc_jump, core_argv, core_kw
        fnex = pyc_jump.get(fn, undefined)
        # print("(CorePy)%s(*%r,**%r) Calls" % (fn, core_argv, core_kw), fnex )
        try:
            return fnex(*core_argv, **core_kw)
        except:
            return undefined
        finally:
            core_kw.clear()
            core_argv.clear()

    def core_pyv(v):
        # print('(CorePy)added', v)
        core_argv.append(v)

    embed.set_ffpy(core_py)
    embed.set_ffpy_add(core_pyv)


class _:
    def __enter__(self):
        embed.disable_irq()

    def __exit__(self, type, value, traceback):
        embed.enable_irq()


aio.block = _()


class _:
    def __enter__(self):
        embed.os_hideloop()

    def __exit__(self, type, value, traceback):
        embed.os_showloop()


aio.hide = _()


class _:
    def __enter__(self):
        embed.os_showloop()

    def __exit__(self, type, value, traceback):
        embed.os_hideloop()


aio.show = _()


class aioctx:
    def __init__(self, delta, coro):
        self.coro = coro
        self.tnext = Time.time() + delta
        self.tmout = 0


class _(list):
    current = None

    async def __aenter__(self):
        if self.__class__.current is None:
            self.__class__.current = aioctx(0, None)
        self.append(self.__class__.current)
        self.__class__.current = None
        if self[-1].coro is not None:
            pdb("__aenter__ awaiting", self[-1].coro)
            try:
                return await self[-1].coro
            except KeyboardInterrupt:
                aio.paused = None
                aio.loop.call_soon(aio.loop.stop)
                pdb("326: aio exit on KeyboardInterrupt")
                return await aio.sleep(0)
        else:
            print('__aenter__ no coro')
            self.__class__.current = None
            return self

    async def __aexit__(self, type, value, traceback):
        len(self) and self.pop()

    def __enter__(self):
        self.append(0)

    def __exit__(self, type, value, traceback):
        len(self) and self.pop()

    def __bool__(self):
        if self.__class__.current:
            return True
        if len(self) and self[-1]:
            return True
        return False

    def __call__(self, frametime):
        print('__call__', len(self), frametime)
        self.__class__.current = aioctx(frametime, None)
        return self

    def call(self, coro):
        print('.call', len(self), coro)
        if self.__class__.current is None:
            self.__class__.current = aioctx(0, coro)
        else:
            self.__class__.current.coro = coro
        # self.__class__.current.tmout = tmout
        return self


aio.ctx = _()
