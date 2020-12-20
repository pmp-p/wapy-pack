import inspect
import asyncio
import asyncio.futures as futures
from asyncio import *

import socket as usocket

def socket(af=usocket.AF_INET):
    sock = usocket.socket(af, usocket.SOCK_DGRAM)
    sock.setblocking(False)
    return sock

CancelledError = futures.concurrent.futures.CancelledError

OrgTask = Task

core = udp = sys.modules[__name__]




class Task(OrgTask):

    def _step(self, value=None, exc=None):
        assert not self.done(), \
            '_step(): already done: {!r}, {!r}, {!r}'.format(self, value, exc)
        if self._must_cancel:
            if not isinstance(exc, CancelledError):
                exc = CancelledError()
            self._must_cancel = False
        coro = self._coro
        self._fut_waiter = None

        self.__class__._current_tasks[self._loop] = self
        # Call either coro.throw(exc) or coro.send(value).
        try:
            if exc is not None:
                result = coro.throw(exc)
#            elif value is not None:
            else:
                result = coro.send(value)
#            else:
#                result = next(coro)

        except StopIteration as exc:
            self.set_result(exc.value)
        except CancelledError as exc:
            super().cancel()  # I.e., Future.cancel(self).
        except Exception as exc:
            self.set_exception(exc)
        except BaseException as exc:
            self.set_exception(exc)
            raise
        else:
            if isinstance(result, futures.Future):
                # Yielded Future must come from Future.__iter__().
                if result._asyncio_future_blocking:
                    result._asyncio_future_blocking = False
                    result.add_done_callback(self._wakeup)
                    self._fut_waiter = result
                    if self._must_cancel:
                        if self._fut_waiter.cancel():
                            self._must_cancel = False
                else:
                    self._loop.call_soon(
                        self._step, None,
                        RuntimeError(
                            'yield was used instead of yield from '
                            'in task {!r} with {!r}'.format(self, result)))
            elif result is None:
                # Bare yield relinquishes control for one event loop iteration.
                self._loop.call_soon(self._step)
            elif inspect.isgenerator(result):
                #print("Scheduling", result)
                self._loop.create_task(result)
                self._loop.call_soon(self._step)
                # Yielding a generator is just wrong.
#                self._loop.call_soon(
#                    self._step, None,
#                    RuntimeError(
#                        'yield was used instead of yield from for '
#                        'generator in task {!r} with {}'.format(
#                            self, result)))
            else:
                # Yielding something else is an error.
                self._loop.call_soon(
                    self._step, None,
                    RuntimeError(
                        'Task got bad yield: {!r}'.format(result)))
        finally:
            self.__class__._current_tasks.pop(self._loop)
            self = None  # Needed to break cycles when an exception occurs.


asyncio.tasks.Task = Task


OrgStreamWriter = StreamWriter

class StreamWriter(OrgStreamWriter):

    def awrite(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.write(data)
        yield from self.drain()

    def aclose(self):
        self.close()
        return
        yield


asyncio.streams.StreamWriter = StreamWriter

# also NameError before 3.8

# Within a coroutine, simply use `asyncio.get_running_loop()`, since the coroutine wouldn't be able
# to execute in the first place without a running event loop present.
try:
    loop = get_running_loop()
except RuntimeError:
   # depending on context, you might debug or warning log that a running event loop wasn't found
   loop = get_event_loop()

def run_once(*argv,**kw):
    global loop
    loop.call_soon(loop.stop)
    loop.run_forever()

loop.run_once = run_once

async def sleep_ms(t):
    await sleep(float(t)/1_000)

del run_once

