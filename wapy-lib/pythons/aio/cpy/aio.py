# ❯❯❯
import sys
import json

DBG = 0

paused = False
failures = 0
pstab = {}

# prg q , index is an ID
q = {}

# ioctl q , index is a fd AND a timestamp
ctl = []


req = []
cycle = 1

try:pdb
except:pdb = print

import uasyncio
from uasyncio import *

loop = get_event_loop()

asleep = sleep

async def sleep_ms(ms):
    await sleep(float(ms)/1000)


def finalize(*argv,**kw):
    pdb('30:','aio.finalize()')


# TODO: pause only non critical coro

def step(*argv, **kw):
    global loop, paused, cycle, schedule, failures, q, ctl

    cycle += 1
    if len(argv) and failures<5:
        try:
            for jsdata in argv:
                if isinstance(jsdata, list):
                    #  just boxed pointers lists (java style) ?
                    embed.log(f"68: {jsdata}")
                    ser = jsdata.pop(0)
                    q.update( {ser:jsdata} )
                    continue

                # or nested json
                if not isinstance(jsdata,str):
                    if cycle<100:
                        embed.log(f"44: bad link not json : {type(jsdata)} {jsdata}")
                    continue

                jsdata = json.loads(jsdata)

                # remote ioctl (javascript style link) ?
                if isinstance(jsdata, dict):
                    if 'ioctl' in jsdata:
                        ctl.extend( jsdata.pop('ioctl') )
                        if cycle<100:
                            embed.log(f"51: N/I ioctl {jsdata}")
                    q.update(jsdata)
                    continue


        except Exception as e:
            failures +=1
            embed.log(f"aio.step link error {e} stack {argv}")

    if failures > 10:
        embed.log(f"64:aio.step emergency stop")
        return

    loop.call_soon(loop.stop)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        paused = True
    except RuntimeError as e:
        pdb(f"55:aio loop broke on run_forever {repr(e)}")
        sys.print_exception(e,sys.stderr)
    except Exception as e:
        failures+=1
        pdb('58:aio broke #', failures,'at',cycle)
        sys.print_exception(e,sys.stderr)


































#
