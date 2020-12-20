# ❯❯❯

import embed
import sys, os, builtins, time

import json

builtins.sys = sys
builtins.os = os
builtins.embed = embed
builtins.builtins = builtins

builtins.python3 = sys.modules[__name__]

# no dll/so hook when in host "emulator"
if not __UPY__:
    import io

    # setup exception display with same syntax as upy
    import traceback

    def print_exception(e, out=sys.stderr, **kw):
        try:
            if hasattr(Applications.MainActivity,'cc') and out==sys.stderr:
                buf = StringIO()
                kw["file"] = buf
                traceback.print_exc(**kw)
                Applications.MainActivity.cc.send(buf)
                return
        except:
            pass

        kw["file"] = out
        traceback.print_exc(**kw)

    sys.print_exception = print_exception
    del print_exception

    # test for this implementation ctytpes support

    try:
        import ctypes
    except Exception as e:
        ctypes = None
        sys.print_exception(e)

    if hasattr(sys, "getandroidapilevel"):
        builtins.__EMU__ = False
        from .aosp import *
    else:
        print("running in host emulator or wasm")
        builtins.__EMU__ = True
        builtins.__ANDROID__ = not __EMSCRIPTEN__

    try:

        # javascript stdio
        if __EMSCRIPTEN__:
            import binascii
            import embed

            original_stderr_fd = sys.stderr.fileno()
            original_stdout_fd = sys.stdout.fileno()

            class Redir(object):
                def __init__(self, channel, file):
                    self.channel = channel
                    self._file = file  # no = fileno
                    self.buf = []



                def write(self, s):
                    self.buf.append(s)
                    # classic buffers behaviour
                    # if self.buf[-1].find('\n')>=0:

                    # wanted behaviour
                    if self.buf[-1].endswith("\n"):
                        self.flush()

                def flush(self):
                    s = "".join(self.buf)
                    #s = s.replace("\n", "↲")  # ¶
                    #s = s.replace("\n", "↲\r\n")

                    # line cooking
                    s = s.replace("\n", "\r\n")
                    if len(s):
                        embed.demux_fd(1, s)
                        #value = binascii.hexlify(s.encode('utf-8')).decode('utf-8')
                        #embed.demux_fd(  json.dumps( { 1 : value } ) )

                        #embed.cout(f'"sys.{self.channel}" : "{s}"')

                        #sys.__stdout__.write( json.dumps( { 1 : value } ) )
                        #sys.__stdout__.write( "\n" )
                        #sys.__stdout__.flush()
                    self.buf.clear()


                def __getattr__(self, attr):
                    if attr[0] == "_":
                        return object.__getattribute__(self, attr)
                    return getattr(self._file, attr)

            sys.stdout = Redir("1", sys.stdout)
            sys.stderr = Redir("2", sys.stderr)

        # android stdio
        elif not __EMU__:


            original_stderr_fd = sys.stderr.fileno()
            original_stdout_fd = sys.stdout.fileno()

            class LogFile(object):
                def __init__(self, channel, file):
                    self.channel = channel
                    self._file = file  # no = fileno
                    self.buf = []

                def write(self, s):
                    self.buf.append(s)
                    # classic buffers behaviour
                    # if self.buf[-1].find('\n')>=0:

                    # wanted behaviour
                    if self.buf[-1].endswith("\n"):
                        s = "".join(self.buf)
                        s = s.replace("\n", "↲")  # ¶
                        if len(s):
                            embed.cout(f"sys.{self.channel}: {s}")
                        self.buf.clear()

                def flush(self):
                    return

                def __getattr__(self, attr):
                    if attr[0] == "_":
                        return object.__getattribute__(self, attr)
                    return getattr(self._file, attr)

            sys.stdout = LogFile("stdout", sys.stdout)
            sys.stderr = LogFile("stderr", sys.stderr)

        if ctypes:
            try:
                builtins.libc = ctypes.CDLL("libc.so")
            except OSError:
                builtins.libc = None

        try:
            # add the pip packages folder or in-apk
            addsys = []
            ipos = 0
            for pos, syspath in enumerate(sys.path):
                if syspath.endswith("/assets"):
                    addsys.append(f"{syspath}/packages")
                    if not ipos:
                        ipos = pos

            print("sys.path=", sys.path)
            while len(addsys):
                sys.path.insert(ipos + 1, addsys.pop(0))
                print(f" -> added {sys.path[ipos+1]}")
            del addsys

            if __EMSCRIPTEN__ and embed.js_int('Module["norepl"]'):
                embed.js_eval("Module.setStatus('Done!')");
            else:
                try:
                    import Applications
                    Applications.onCreate(Applications, python3)
                except Exception as e:
                    sys.print_exception(e)

#            if not __EMU__:
#                for k in os.environ:
#                    print(f"    {k} = '{os.environ[k]}'")

        except Exception as e:
            embed.log(f"FATAL: {__file__.split('assets/')[-1]} {e}")
            sys.print_exception(e)

    except Exception as e:
        try:
            sys.print_exception(e)
        except:
            embed.log("161: %r" % e )

    import time as Time
else:
    import utime as Time


import pythons.aio.plink

# TODO: in case of failure to create "Applications" load a safe template
# that could display the previous tracebacks

try:
    Applications
except:
    class MainActivity:

        async def __main__(*self):
            print("215: broken MainActivity.__main__")
        async def test(*self):
            print("217: broken MainActivity.test")


    class Applications:

        MainActivity = MainActivity()

        @staticmethod
        def onCreate(self, pyvm):
            print("404:onCreate", pyvm)
            # empty module

        @staticmethod
        def onStart(self, pyvm):
            print("404:onStart", pyvm)
        @staticmethod
        def onPause(self, pyvm):
            print("404:onPause", pyvm)
        @staticmethod
        def onResume(self, pyvm):
            print("404:onResume", pyvm)
        @staticmethod
        def onStop(self, pyvm):
            print("404:onStop", pyvm)
        @staticmethod
        def onDestroy(self, pyvm):
            print("404:onDestroy", pyvm)

    del MainActivity

builtins.Applications = Applications

try:
    State = Applications.MainActivity.plink.CallPath.proxy
except Exception as e:
    State = pythons.aio.plink.CallPath.proxy

# =====================================================================

OneSec = time.Lapse(1)
lastc = 0
wall_s = 0
tested = False
jcount = 0
errored = []

def error(self, *msg):
    pdb(*msg)


def dispatch(jsonargs):
    global errored, python3

    if not "aio" in errored:
        try:
            aio.step("{}")
        except Exception as e:
            pdb("276: aio.stepping error:", e)
            sys.print_exception(e)
            errored.append( "aio" )

    if isinstance(jsonargs, str):
        method, argv = json.loads(jsonargs)
    else:
        method = jsonargs.pop(0)
        argv = jsonargs

    callstack = []

    if isinstance(method, str):
        if not method in errored:

            rv = None
            if hasattr(Applications, method):
                try:
                    rv = getattr(Applications, method)(Applications, python3, *argv)
                except Exception as e:
                    errored.append( method )
                    try:
                        print("298: dispatch(",method,") error",e)
                        sys.print_exception(e)
                    except:
                        embed.log("292: %r" % e )

                # maybe use rv to select ui/non ui
                # if rv is not None:
                #    callstack.append( rv )
            else:
                errored.append( method )
                print("307: *************** FAIL: dispatch '{}'".format(method), jsonargs)
    else:
        print("303: RPC garbage")

    try:
        # normal calls can go on all threads
        callstack.extend(State.q_sync)
        if State.ui:
            callstack.extend(State.q_async)
        embed.run(json.dumps(callstack))

    finally:
        State.q_sync.clear()
        if State.ui:
            State.q_async.clear()
            # State.ui = False


def on_event(apps, p3, evid):
    evh = apps.MainActivity.Events.ld.get(evid, None)
    if evh is None:
        print("event ignored : ", evid)
        return
    sender, target, handler, hint = evh
    aio.loop.create_task(handler(sender, target, hint))


def onui(apps, p3, *in_queue):
    State.ui = True
    if len(State.q_ui):
        print("onui", State.q_ui)

def oncursor(apps, p3, e ):
    print("oncursor", e)

def onmouse(apps, p3, *in_queue ):
    oid, etype, cx, cy = in_queue
    clients = apps.MainActivity.Events.ev.get(etype,{}).get(oid, [])
    if len(clients):
        e = {'type':etype,'x':cx,'y':cy}
        for client in clients:
            client( e )
        #print("dispatched !", e)
        return
    else:
        pass
        #print("dispatch->onmouse",in_queue)


def on_step(apps, p3):
    global OneSec, wall_s, lastc, tested, jcount
    jcount += 1

    if OneSec:
        wall_s += 1
        if wall_s == 5 and not tested:
            if os.path.isdir(f"assets/python{sys.version_info.major}.{sys.version_info.minor}/test"):
                print("starting testsuite")
                import test.__main__
            else:
                embed.log("============= THE TEST : Begin =================")
                aio.loop.create_task(apps.MainActivity.test())
                tested = True

        if wall_s == 10:
            print("FPS ", (jcount - lastc) / wall_s)
            lastc = jcount + 1
            wall_s = 0
            if libc:libc.puts(b"c.status = %d" % jcount)
            print(f"step {jcount}")


try:
    # bind default handler to applications framework if not overridden
    for attr in ('onui','onmouse','on_event','on_step'):
        if not hasattr(Applications, attr):
            setattr(Applications, attr, getattr(python3,attr) )

    builtins.Applications = Applications
except:
    builtins.Applications = python3


