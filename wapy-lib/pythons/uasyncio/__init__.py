# (c) 2014-2018 Paul Sokolovsky. MIT license.

# (c) 2019- Pmp P. MIT license.


#       The POSIX AIO interface consists of the following functions:
#
#       aio_read(3)     Enqueue a read request.  This is the asynchronous
#                       analog of read(2).
#
#       aio_write(3)    Enqueue a write request.  This is the asynchronous
#                       analog of write(2).
#
#       aio_fsync(3)    Enqueue a sync request for the I/O operations on a
#                       file descriptor.  This is the asynchronous analog of
#                       fsync(2) and fdatasync(2).
#
#       aio_error(3)    Obtain the error status of an enqueued I/O request.
#
#       aio_return(3)   Obtain the return status of a completed I/O request.
#
#       aio_suspend(3)  Suspend the caller until one or more of a specified
#                       set of I/O requests completes.
#
#       aio_cancel(3)   Attempt to cancel outstanding I/O requests on a
#                       specified file descriptor.
#
#       lio_listio(3)   Enqueue multiple I/O requests using a single function
#


# TODO: keep track of the multiple __main__  and handle their loop separately
# as subprograms
# TODO: contextvars

import sys

# keep parso happy
def make_type_gen():
    return type((lambda: (yield))())
type_gen = make_type_gen() #= type((lambda: (yield))())


def iscoroutine(f):
    global type_gen
    return isinstance(f, type_gen)


# import ucollections
import utimeq

try:
    import utime as Time
except:
    try:
        import time as Time
    except:
        print("56: FATAL: Time failure")

try:
    import uselect as select
except:
    print(f"TODO: a select.poll() implementation is required {sys.platform=}")


if __EMSCRIPTEN__:
    import embed

    wall_init = embed.time_ms()

    def wait_ms(argv):
        pass

    ticks_add = embed.ticks_add
    ticks_diff = embed.ticks_diff

    def ticks_ms():
        global init_ms
        return embed.time_ms() - wall_init

    embed.log("81: #FIXME: uasyncio/__init__.py with time.time_ns() PEP 564")
    # https://www.python.org/dev/peps/pep-0564/
    # https://vstinner.github.io/python37-pep-564-nanoseconds.html

    class select:
        class fake_poll:
            def register(self, *argv):
                print("register", argv)

            def unregister(self, *argv):
                print("register", argv)

            def ipoll(*self):
                # print("ipoll",self)
                return ()

        instance = fake_poll()

        @classmethod
        def poll(cls):
            return cls.instance


if 1:
    init_ms = Time.ticks_ms()
    ticks_diff = Time.ticks_diff
    wait_ms = Time.sleep_ms
    ticks_ms = Time.ticks_ms
    ticks_add = Time.ticks_add


cur_task = [0, 0, 0]

auto = 0
# for asyncio tasks
failure = False

# for io errors ( dom==gpu / websocket==socket  )
io_error = False

loop = None


def task(t, *argv, **kw):
    global loop
    if loop is None:
        loop = get_running_loop()
    print("about to start %s(*%r,**%r)" % (t.__name__, argv, kw))
    loop.create_task(t(*argv, **kw))


def __auto__():
    global loop, auto
    if auto:
        try:
            return loop.run_once()
        except Exception as e:
            auto = None
            sys.print_exception(e)
            print("asyncio, panic stopping auto loop", file=sys.stderr)
    return None


class CancelledError(Exception):
    pass


class TimeoutError(CancelledError):
    pass


class EventLoop:
    def __init__(self, runq_len=16, waitq_len=16):
        self.runq = []  # ucollections.deque((), runq_len, True)
        self.waitq = utimeq.utimeq(waitq_len)

        # Current task being run. Task is a top-level coroutine scheduled
        # in the event loop (sub-coroutines executed transparently by
        # yield from/await, event loop "doesn't see" them).
        self.cur_task = None
        self.scheduler = []

    def create_task(self, coro, name=None):
        # CPython 3.4.2
        # CPython asyncio incompatibility: we don't return Task object
        if iscoroutine(coro):
            self.call_later_ms(0, coro)
            return
        # CPython asyncio incompatibility: we assume non generator object as scheduled functions pointers
        self.scheduler.append(coro)

    def call_soon(self, callback, *argv):
        self.runq.append(callback)
        if not isinstance(callback, type_gen):
            self.runq.append(argv)

    def call_later(self, delay, callback, *argv):
        self.call_at_(ticks_add(ticks_ms(), int(delay * 1000)), callback, argv)

    def call_later_ms(self, delay, callback, *argv):
        if not delay:
            return self.call_soon(callback, *argv)
        self.call_at_(ticks_add(ticks_ms(), int(delay)), callback, argv)

    def call_at_(self, time, callback, argv=()):
        try:
            self.waitq.push(int(time), callback, argv)
        except OverflowError as e:
            print("OverflowError:", time, callback, argv, e)
            self.waitq.push(int(1), callback, argv)

    def wait(self, delay):
        # Default wait implementation, to be overriden in subclasses
        # with IO scheduling
        wait_ms(delay)

    def run_once(self):
        global cur_task
        tnow = ticks_ms()
        for task in self.scheduler:
            try:
                task()
            except Exception as e:
                sys.print_exception(e)
                try:
                    print(tnow, ":", "task", task.__name__, "removed from scheduler")
                except:
                    print(tnow, ":", "task", task, "removed from scheduler")
                self.scheduler.remove(task)
                # list as changed and give a chance to read error
                return

        delay = 0

        # Expire entries in waitq and move them to runq
        while len(self.waitq):
            delay = ticks_diff(self.waitq.peektime(), tnow)
            if delay > 0:
                break
            self.waitq.pop(cur_task)
            self.call_soon(cur_task[1], *cur_task[2])

        # Process runq
        while len(self.runq):
            cb = self.runq.pop(0)
            argv = ()
            if not isinstance(cb, type_gen):
                if len(self.runq):
                    argv = self.runq.pop(0)
                try:
                    cb(*argv)
                    continue
                except TypeError:
                    print("287:run_once", cb, argv)

            self.cur_task = cb

            try:
                if argv==():
                    ret = next(cb)
                else:
                    ret = cb.send(*argv)

                if isinstance(ret, SysCall1):
                    argv = ret.arg
                    if isinstance(ret, SleepMs):
                        delay = argv
                    elif isinstance(ret, IORead):
                        cb.pend_throw(False)
                        self.add_reader(argv, cb)
                        continue
                    elif isinstance(ret, IOWrite):
                        cb.pend_throw(False)
                        self.add_writer(argv, cb)
                        continue
                    elif isinstance(ret, IOReadDone):
                        self.remove_reader(argv)
                    elif isinstance(ret, IOWriteDone):
                        self.remove_writer(argv)
                    elif isinstance(ret, StopLoop):
                        return argv
                    else:
                        assert False, "Unknown syscall yielded: %r (of type %r)" % (ret, type(ret))

                elif isinstance(ret, type_gen):
                    self.call_soon(ret)
                elif isinstance(ret, int):
                    # Delay
                    delay = ret
                elif ret is None:
                    # Just reschedule
                    pass
                elif ret is False:
                    # Don't reschedule
                    continue
                elif isinstance(ret, float):
                    # Delay
                    delay = int(ret)
                else:
                    assert False, "Unsupported coroutine yield value: %r (of type %r)" % (ret, type(ret))

            except StopIteration as e:
                continue
            except CancelledError as e:
                continue
            # Currently all syscalls don't return anything, so we don't
            # need to feed anything to the next invocation of coroutine.
            # If that changes, need to pass that value below.
            if delay:
                self.call_later_ms(delay, cb)
            else:
                self.call_soon(cb)

        if not __EMSCRIPTEN__:
            # Wait until next waitq task or I/O availability
            delay = 0
            if not len(self.runq):
                delay = -1
                if self.waitq:
                    delay = ticks_diff(self.waitq.peektime(), ticks_ms())
                    if delay < 0:
                        delay = 0
            self.wait(delay)
        return delay

    def run_forever(self):
        global cur_task
        while True:
            self.wait(self.run_once())

    def run_until_complete(self, coro):
        def _run_and_stop():
            yield from coro
            yield StopLoop(0)

        self.call_soon(_run_and_stop())
        self.run_forever()

    def stop(self):
        self.call_soon((lambda: (yield StopLoop(0)))())

    def close(self):
        pass


class SysCall:
    def __init__(self, *argv):
        self.args = argv

    def handle(self):
        raise NotImplementedError


# Optimized syscall with 1 arg
class SysCall1(SysCall):
    def __init__(self, argv):
        self.arg = argv


class StopLoop(SysCall1):
    pass


class IORead(SysCall1):
    pass


class IOWrite(SysCall1):
    pass


class IOReadDone(SysCall1):
    pass


class IOWriteDone(SysCall1):
    pass


def get_event_loop():
    global loop
    if loop is None:
        loop = _event_loop_class(16, 16)
    return loop

def get_running_loop():
    global loop
    return loop

def sleep(secs):
    yield int(secs * 1000)


# Implementation of sleep_ms awaitable with zero heap memory usage
class SleepMs(SysCall1):
    def __init__(self):
        self.v = None
        self.arg = None

    def __call__(self, argv):
        self.v = argv
        # print("__call__")
        return self

    def __iter__(self):
        # print("__iter__")
        return self

    def __next__(self):
        if self.v is not None:
            # print("__next__ syscall enter")
            self.arg = self.v
            self.v = None
            return self
        # print("__next__ syscall exit")
        _stop_iter.__traceback__ = None
        raise _stop_iter


_stop_iter = StopIteration()
sleep_ms = SleepMs()


def cancel(coro):
    if coro.pend_throw(CancelledError()) is False:
        loop.call_soon(coro)


class TimeoutObj:
    def __init__(self, coro):
        self.coro = coro


def wait_for_ms(coro, timeout):
    def waiter(coro, timeout_obj):
        res = yield from coro
        timeout_obj.coro = None
        return res

    def timeout_func(timeout_obj):
        if timeout_obj.coro and (timeout_obj.coro.pend_throw(TimeoutError()) is False):
            loop.call_soon(timeout_obj.coro)

    timeout_obj = TimeoutObj(loop.cur_task)
    loop.call_later_ms(timeout, timeout_func, timeout_obj)
    return (yield from waiter(coro, timeout_obj))


def wait_for(coro, timeout):
    return wait_for_ms(coro, int(timeout * 1000))


# CPython asyncio incompatibility: Task is a function, not a class (for efficiency)
def Task(coro, loop=loop):
    # Same as async()
    loop.call_soon(coro)


class _event_loop_class(EventLoop):
    def __init__(self, runq_len=16, waitq_len=16):
        EventLoop.__init__(self, runq_len, waitq_len)
        self.poller = select.poll()
        self.objmap = {}

    def add_reader(self, sock, cb, *args):
        self.poller.register(sock, select.POLLIN)
        if args:
            self.objmap[id(sock)] = (cb, args)
        else:
            self.objmap[id(sock)] = cb

    def remove_reader(self, sock):
        self.poller.unregister(sock)
        del self.objmap[id(sock)]

    def add_writer(self, sock, cb, *args):
        self.poller.register(sock, select.POLLOUT)
        if args:
            self.objmap[id(sock)] = (cb, args)
        else:
            self.objmap[id(sock)] = cb

    def remove_writer(self, sock):
        try:
            self.poller.unregister(sock)
            self.objmap.pop(id(sock), None)
        except OSError as e:
            # StreamWriter.awrite() first tries to write to a socket,
            # and if that succeeds, yield IOWrite may never be called
            # for that socket, and it will never be added to poller. So,
            # ignore such error.
            if e.args[0] != 2:  # uerrno.ENOENT:
                raise

    def wait(self, delay):
        # We need one-shot behavior (second arg of 1 to .poll())
        #        res = self.poller.ipoll(delay, 1)
        # log.debug("poll result: %s", res)
        # Remove "if res" workaround after
        # https://github.com/micropython/micropython/issues/2716 fixed.

        for sock, ev in self.poller.ipoll(delay, 1):
            cb = self.objmap[id(sock)]
            if ev & (select.POLLHUP | select.POLLERR):
                # These events are returned even if not requested, and
                # are sticky, i.e. will be returned again and again.
                # If the caller doesn't do proper error handling and
                # unregister this sock, we'll busy-loop on it, so we
                # as well can unregister it now "just in case".
                self.remove_reader(sock)
            if isinstance(cb, tuple):
                cb[0](*cb[1])
                continue
            cb.pend_throw(None)
            self.call_soon(cb)
