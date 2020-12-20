# this aio module try to add support for posix aio functions.


import builtins, sys


# if site.py did not patch it, get one
try:
    Time
except:
    try:
        import utime as Time
    except:
        import time as Time
    print("Using normal Time implementation :", Time)
    builtins.Time = Time


# still allow a module named that way
sys.modules.pop("Time", None)


def rtclock():
    return int(Time.time() * 1_000)


aio = sys.modules[__name__]

# aio is a vital component make sure it is wide access.
builtins.aio = aio


# for repl completion
vars(__import__("__main__"))["aio"] = aio

# just in case someday cpython would have it
sys.modules["aio"] = aio


if __UPY__:
    from .upy.aio import *

    # implementation provided builtins
    try:
        suspend = aio_suspend
    except:
        print("WARNING: that Python implementation lacks aio_suspend()", file=sys.stderr)

        def suspend():
            print("50: aio_suspend N/I")

        builtins.aio_suspend = suspend

else:
    from .cpy.aio import *

    if __EMSCRIPTEN__:

        def websocket(*argv, **kw):
            from .upy.websocket import websocket
            return websocket(*argv, **kw)

        def suspend():
            raise Exception("64: aio_suspend unsupported - use a worker")

    else:

        def websocket(*argv, **kw):
            from .cpy.websocket import websocket

            return websocket(*argv, **kw)

        def suspend():
            Time.sleep(0.016)

    builtins.aio_suspend = suspend

# mark not started but no error
aio.error = None

aio.paused = False
aio.fd = {}
aio.pstab = {}


# https://docs.python.org/3/library/threading.html#threading.excepthook

# a green thread
# FIXME: fix wapy BUG 882 so target can be None too in preempt mode

# TODO: default granularity with https://docs.python.org/3/library/sys.html#sys.setswitchinterval


class Thread:
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        global loop, pstab
        self.args = args
        self.kwargs = kwargs
        self.name = name
        self.slice = 0
        self.last = aio.rtclock()

        if target:
            if hasattr(target, "run"):
                if name is None:
                    self.name = name or target.__class__.__name__
                self.run = target.run
            else:
                self.run = target

            if name is None:
                try:
                    self.name = "%s-%s" % (self.run.__name__, id(self))
                except:
                    pass
        else:
            target = self

        if self.name is None:
            self.name = "%s-%s" % (self.__class__.__name__, id(self))
        self.status = None


    async def runner(self, coro):
        self.status = True
        try:
            # TODO: pass thread local context here
            async with aio.ctx(self.slice).call(coro):
                self.status = False
        except Exception as e:
            self.status = repr(e)
            sys.print_exception(e, sys.stderr)

    if __UPY__:

        def __iter__(self):
            if self.status is True:
                rtc = aio.rtclock()
                self.delta = (rtc - self.last) - self.slice
                if self.delta < 0:
                    self.delta = 0
                yield from aio.sleep_ms(self.slice - int(self.delta / 2))
                self.last = rtc

        __await__ = __iter__
    else:

        def __await__(self):
            if self.status is True:
                rtc = aio.rtclock()
                self.delta = (rtc - self.last) - self.slice
                if self.delta < 0:
                    self.delta = 0
                # no sleep_ms on cpy
                yield from aio.sleep_ms( float(self.slice - int(self.delta / 2)) / 1_000 ).__await__()
                #return aio.sleep( float(self.slice - int(self.delta / 2)) / 1_000 )
                self.last = rtc

    def rt(self, slice):
        self.slice = int(float(slice) * 1_000)
        return self

    def start(self):
        global pstab
        pstab.setdefault(self.name, [])
        if self.run:
            coro = self.run(*self.args, **self.kwargs)
            pdb("50:", self.name, "starting", coro)
            loop.create_task(self.runner(coro))
            pstab[self.name].append(self)

        return self

    def join(self):
        embed.enable_irq()
        while self.is_alive():
            aio_suspend()
        embed.disable_irq()

    def __bool__(self):
        return self.is_alive()

    def is_alive(self):
        return self.status is True


# wasm upy does not have it, maybe replace with green threading
# sys.modules['threading'] = aio


def service(srv, *argv, **kw):
    embed.log(f"starting green thread : {srv}")
    thr =  aio.Thread(group=None, target=srv, args=argv, kwargs=kw).start()
    srv.__await__ = thr.__await__
    return pstab.setdefault(srv, thr  )
aio.task = service


def proc(srv):
    return pstab.get(srv)

class Runnable:

    def __await__(self):
        yield from pstab.get(self).__await__()


def start(argv, env, **kw):
    global paused
    if aio.error is True:
        return pdb("80: aio can't start with uncleared error")

    if aio.error is False:
        return pdb("80: aio can't start twice")

    try:
        corofn = getattr(__import__("__main__"), "main")
        embed.log(f"run async main : {corofn}")
        loop.create_task(corofn(len(argv), argv, env))
        aio.error = False
        paused = False
    except Exception as e:
        aio.error = True
        embed.log(f"run async main failed : {e}")


# cpython asyncio compat
try:
    _shutdown
except:

    def _shutdown(*argv, **kw):
        print("_shutdown")


def run(coro, **kw):
    global loop
    # TODO: kw.get('debug',False)
#    if hasattr(coro,'__name__'):
#        loop.create_task(coro, name=coro.__name__)
#    else:
#        loop.create_task(coro, name=repr(coro))
    loop.create_task(coro)
    aio.error = False


if __UPY__ and __EMSCRIPTEN__:
    try:
        from .browser import *
    except Exception as e:
        pdb("Failed to load browser support")
        sys.print_exception(e)


def create_task(coro,**kw):
    global loop
    # TODO: expand name to fq name
    loop.create_task(coro, name=kw.get('name',coro.__name__))
