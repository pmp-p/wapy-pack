# a generic async proxy, most command are batched in a queue
# the proxy has no knowledge of RPC schema, and it won't list method/props etc
# use HOST documentation for that.
# if you need an immediate result use  .finalize or async with object:
# .finalize is a sort of .gather() for all requests pending on 1 callpath
# callpahs have roots that match host namespaces:
#  on browser js its "window" , on aosp its "android"



# the method used is slow : lots of new proxies are created along the path
# idea :  hash all the call paths in the same instance ...
# and add a key/values db/shelf for props.

# TODO: benchmark the both methods.

# TODO: records callpaths for the different hosts to document the most usefull of them
# and later build native accelerators (eg  jnius / rubicon / typescript-wasm ... )


DBG = 0
ADBG = 0
SDBG = 0

# __ANDROID__ and __UPY__ should be set by 'pythons'

if __UPY__:
    import embed
    from ujson import dumps, loads
    import ubinascii as binascii
else:
    import sys
    import binascii
    from json import dumps, loads

import builtins

from pythons import aio

from collections import namedtuple

def convert(obj, cn='GenericDict'):
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            obj[key] = convert(value)
        return namedtuple(cn, obj.keys())(**obj)
    elif isinstance(obj, list):
        return [convert(item) for item in obj]
    else:
        return obj


async def get(coro):
    obj = loads( await coro )
    cn = obj.pop('class')
    return convert(obj, cn)


class BaseProxy:
    @classmethod
    def ni(cls, *argv, **kw):
        print(cls, 'N/I', argv, kw)

    get = ni
    act = ni
    set = ni
    tmout = 1000
    cfg = {"get": {}, "set": {}, "act": {}}

    def new_call(self):
        self.caller_id += 1
        return str(self.caller_id)



class obj:
    def __init__(self):
        self.myattr = 666

    def __delattr__(self, name):
        print('delattr ', name)



class CallPath(dict):

    proxy = None #BaseProxy
    cache = {}
    aioq = []



    def __setup__(self, host, fqn, csp, default=None, tip='[object %s]'):
        self.__fqn = fqn
        self.__name = fqn.rsplit(".", 1)[-1]
        self.__host = host
        self.__solved = undefined
        self.__aself = None

        if not self in CallPath.aioq:
            CallPath.aioq.append(self)

        # that shoul be an empty call stack pipeline for new object paths.
        self.__csp = csp
        self.__tmout = BaseProxy.tmout
        self.__tip = tip
        if host:
            self.__host._cp_setup(self.__name, default)
        return self

    @classmethod
    def set_proxy(cls, proxy):
        cls.proxy = proxy
        proxy.cp = cls
        cls.get = proxy.get
        cls.set = proxy.set
        cls.act = proxy.act

    def __delattr__(self, name):
        print('delattr ', name)

    def __getattr__(self, name):
        if name == 'finalize':
            csp = list(self.__csp)
            self.__csp.clear()
            while len(csp):
                flush = csp.pop(0)
                self.proxy.act(*flush)  # does discard
            #gc only at end of "async with" batching
            if not len(CallPath.aioq):
                aio.finalize()
            return None

        if name in self:
            return self[name]

        fqn = "%s.%s" % (self.__fqn, name)
        if DBG:
            if len(self.__csp):
                print(f"13x: cp-ast {fqn} with PARENT call(s) pending", *self.__csp)
            else:
                print(f"13x: cp-ast {fqn}")

        newattr = self.__class__().__setup__(self, fqn, self.__csp)

        self._cp_setup(name, newattr)
        return newattr


    def __setattr__(self, name, value):
        if name.startswith("_"):
            self[name] = value
            return

        # print('setattr',name,value)
        fqn = "%s.%s" % (self.__fqn, name)
        #if DBG: print(f"102: cp->pe {fqn} := {value}",*self.__csp)
        self.finalize

#        if len(self.__csp):
#            self.proxy.set(fqn, value, self.__csp)
#            self.__csp.clear()
#            # can't assign path-end to a dynamic callpath
#            return

        # FIXME: caching type/value is flaky
        # setattr(self.__class__, name, PathEnd(self, fqn, value))
        self.proxy.set(fqn, value)

    # FIXME: caching type/value is flaky
    #    def __setitem__(self, name, v):
    #        fqn = "%s.%s" % (self.__fqn, name)
    #        setattr(self.__class__, key, PathEnd(host, fqn, default=v))

    def _cp_setup(self, key, v):
        if v is None:
            if DBG:
                print(f"169: cp-set {self.__fqn}.{key}, NOREF => left unset")
            return


        elif DBG:
            if len(self.__csp):
                print(f"175: cp-set {self.__fqn}.{key} <= {v} with call(s) PARENT pending", *self.__csp)
            else:
                print(f"177: cp-set {self.__fqn}.{key} <= {v}", *self.__csp)

        if not isinstance(v, self.__class__):
            print(f"180: cp-set {key} := {v} ")
            if self.__class__.set:
                if DBG:
                    print("183:cp-set", key, v)
                self.proxy.set("%s.%s" % (self.__fqn, key), v)

        dict.__setitem__(self, key, v)

    async def __solver(self):
        cs = []
        p = self
        while p.__host:
            if p.__csp:
                cs.extend(p.__csp)
            p = p.__host
        cs.reverse()

#TESTING
        p.__csp.clear()
#

        unsolved = self.__fqn
        cid = '?'
        # FIXME: (maybe) for now just limit to only one level of call()
        # horrors like "await window.document.getElementById('test').textContent.length" are long enough already.
        if len(cs):
            solvepath, argv, kw = cs.pop(0)
            cid = self.proxy.act(solvepath, argv, kw)
            if ADBG or SDBG:
                print(self.__fqn, '205:__solver about to wait_answer(%s)' % cid, solvepath, argv, kw)
            self.proxy.q_req.append(cid)
            self.__solved, unsolved = await self.proxy.wait_answer(cid, unsolved, solvepath)

            # FIXME:         #timeout: raise ? or disconnect event ?
            # FIXME: strip solved part on fqn and continue in callstack

            if ADBG or SDBG:
                print(self.__fqn, '214:__solver got wait_answer(%s)' % cid, self.__solved)

            if not len(unsolved):
                return self.__solved
        else:
            if ADBG or SDBG:
                print('217:__solver about to get(%s)' % unsolved)

            if __UPY__:
                self.__solved = await self.proxy.get(unsolved, None)
                return self.__solved
            else:
                return await self.proxy.get(unsolved, None)

        return 'future-async-unsolved[%s->%s]' % (cid, unsolved)

    if __UPY__:

        def __iter__(self):
            if ADBG:print("230:cp-(async)iter", self.__fqn,*self.__csp)
            yield from self.__solver()
            try:
                return self.__solved
            finally:
                self.__solved = undefined

    else:
        # uasyncio __await__ not called
        # https://github.com/micropython/micropython/issues/2678
        def __await__(self):
            if ADBG:print("207:cp-(async)await", self.__fqn,*self.__csp)
            return self.__solver().__await__()


    def __call__(self, *argv, **kw):
        if DBG or SDBG:
            print("251:cp-call (a/s)?", self.__fqn, argv, kw)


        # stack up the (a)sync call list
        self.__csp.append([self.__fqn, argv, kw])

        # async is still the only cpython way
        # this block will only work on wapy


#            aio.loop.create_task( self.__solver() )
#            tmout = 20
#            while tmout and (self.__solved is undef):
#                import aio_suspend
#                print('wait',tmout)
#                tmout -= 1
#            try:
#                return self.__solved
#            finally:
#                self.__solved = undefined
        return self


    def __enter__(self):
        if DBG:print("258:cp-enter")
        return self

    async def __aenter__(self):
        if ADBG:print("262:cp-(async)enter", self.__fqn,*self.__csp)
        self.__aself = await self
        return self.__aself


    def __exit__(self, type, value, traceback):
        # this is a non-awaitable batch !
        #  need async with !!!!!!
        self.finalize
        # do io claims cleanup
        aio.finalize()

        print("#FIMXE: __del__ on proxy to release js obj")

    async def __aexit__(self, type, value, traceback):
        if ADBG:print("277:cp-(async)exit", self.__fqn,len(CallPath.aioq)) #*self.__csp)
        while len(CallPath.aioq):
            aself = CallPath.aioq.pop(0)
            aself.finalize
            await aio.asleep(0)



    # maybe yield from https://stackoverflow.com/questions/33409888/how-can-i-await-inside-future-like-objects-await
    #        async def __call__(self, *argv, **kw):
    #
    #            self.__class__.act(self.__fqn, argv, kw)
    #            cid  = str( self.__class__.caller_id )
    #            rv = ":async-cp-call:%s" % cid
    #            while True:
    #                if cid in self.q_return:
    #                    oid = self.q_return.pop(cid)
    #                    if oid in self.cache:
    #                        return self.cache[oid]
    #
    #                    rv = self.__class__(None,oid)
    #                    self.cache[oid]=rv
    #                    break
    #                await sleep_ms(1)
    #            return rv

# TODO: make non optimized verbose func for non wapy-vm sending warnings for sync calls
    def _(self, tmout):
        if not aio.ctx:
            self.finalize
            return aio.await_for(self.__solver(), tmout )


    def __repr__(self):
        # if self.__fqn=='window' or self.__fqn.count('|'):
        # print("FIXME: give tip about remote object proxy")
        if self.__tip.count('%s'):
            return self.__tip % self.__fqn
        return self.__tip
        # raise Exception("Giving cached value from previous await %s N/I" % self.__fqn)

        # return ":async-pe-get:%s" % self.__fqn

    def __str__(self):
        return self.__fqn


    if not __ANDROID__:

        # dom "optimizers"

        def __lshift__(self, o):
            aio.vm.dom.lshift(str(self),str(o))
            aio.vm.dom.finalize


if __ANDROID__:
    from .plink_android import AndroidProxy as Proxy
    CallPath.set_proxy(Proxy())
    android = CallPath().__setup__(None, 'android', [], tip="[ api android ]")
    androidx = CallPath().__setup__(None, 'androidx', [], tip="[ api androidx ]")
    this = CallPath().__setup__(None, "p:self", [], tip="MainActivity")
    layout = CallPath().__setup__(None, "p:ui", [], tip="Layout")
else:

# ======================================================================================

    # js proxy

    class Proxy(BaseProxy):
        def __init__(self):
            self.caller_id = 0
#            self.tmout = 1000 # ms
            self.cache = {}
            aio.DBG=1
            self.q_return = aio.q  # {}
            self.q_req = aio.req # []

            self.q_reply = []
            self.q_sync = []

            self.q_async = []




        if __UPY__:
            def io(self, cid,raw=None, m=None, jscmd=None):
                if jscmd:
                    #print("\n  >> io=",cid, jscmd)
                    jscmd = binascii.hexlify( jscmd ).decode()
                    embed.os_write( '{"dom-%s":{"id":"%s","m":"//%c:%s"}}\n' % (cid, cid,m, jscmd) )
                elif raw:
                    #print("\n  >> io=",cid, raw)
                    embed.os_write( raw )
                #print()
                return cid
        elif __ANDROID__:
            def io(self, cid, raw=None, m=None, jscmd=None):
                if jscmd:
                    print("\n  >> io=",cid, jscmd)
                    #jscmd = binascii.hexlify( jscmd.encode('utf-8') ).decode('utf-8')
                    #sys.__stdout__.write( 'TODO: {"dom-%s":{"id":"%s","m":"//%c:%s"}}\n' % (cid, cid,m, jscmd) )
                elif raw:
                    print("\n  >> io=",cid, raw)
                    #sys.__stdout__.write( raw )
                return cid

        else:
            def io(self, cid,raw=None, m=None, jscmd=None):
                if jscmd:
                    #print("\n  >> io=",cid, jscmd)
                    jscmd = binascii.hexlify( jscmd.encode('utf-8') ).decode('utf-8')
                    sys.__stdout__.write( '{"dom-%s":{"id":"%s","m":"//%c:%s"}}\n' % (cid, cid,m, jscmd) )
                elif raw:
                    #print("\n  >> io=",cid, raw)
                    sys.__stdout__.write( raw )
                #print()
                return cid


        def unref(self, cid):
            if cid in self.q_req:
                self.q_req.remove(cid)
            else:
                print('315: %s was never awaited'%cid)

            oid = self.q_return.pop(cid)

            if DBG:
                print("448: removing response %r = %s" % (cid,oid) )

            if isinstance(oid, str) and oid.startswith('js|'):
                tip = "%s@%s" % (oid, cid)

                if oid.find('/') > 0:
                    oid, tip = oid.split('/', 1)

                if not oid in self.cache:
                    #create a new pipeline for the ref object
                    self.cache[oid] = CallPath().__setup__(None, oid, [], tip=tip)
            return oid, self.cache.get(oid, oid )




        def set(self, cp, argv, cs=None):
            cid = self.new_call()
            if cs is not None:
                if len(cs) > 1:
                    raise Exception('please simplify assign via (await %s(...)).%s = %r' % (cs[0][0], cp, argv))
                solvepath, targv, kw = cs.pop(0)
                unsolved = cp[len(solvepath) + 1 :]

                jsdata = f"JSON.parse(`{dumps(targv)}`)"
                target = solvepath.rsplit('.', 1)[0]
                assign = f'JSON.parse(`{dumps(argv)}`)'
                doit = f"{solvepath}.apply({target},{jsdata}).{unsolved} = {assign}\n"
                #if DBG:
                #    print("74:", doit)

                # TODO: get js exceptions ?
                self.io( cid, raw=doit)

                return

            if cp.count('|'):
                cp = cp.split('.')
                cp[0] = f'window["{cp[0]}"]'
                cp = '.'.join(cp)

            if DBG:
                print('306: set', cp, argv)

            if isinstance(argv,str):
                argv = argv.replace('"', '\\\"')

            # TODO: get js exceptions ?
            jscmd = f'{cp} = JSON.parse(`{dumps(argv)}`)'
            self.io( cid , m='S', jscmd=jscmd)
            #


        async def get(self, cp, argv, **kw):
            cid = self.new_call()
            self.q_req.append(cid)

            # IO
            self.io(cid,raw='{"dom-%s":{"id":"%s","m":"%s"}}\n' % (cid, cid, cp))
            # test

            while True:
                if self.q_return:
                    if cid in self.q_return:
                        self.q_req.remove(cid)
                        return self.q_return.pop(cid)
                await aio.sleep_ms(1)

        # act will discard results, if results are needed you MUST use await
        def act(self, cp, c_argv, c_kw, **kw):
            # self.q_async.append( {"m": cp, "a": c_argv, "k": c_kw, "id": cid} )
            cid = self.new_call()
            # TODO: get js exceptions ?
            c_argv = dumps(c_argv)
            c_kw = dumps(c_kw)
            raw = '{"dom-%s":{"id":"%s","m":"%s", "a": %s, "k": %s }}\n' % (cid, cid, cp, c_argv, c_kw)
            return self.io( cid , raw=raw) # return cid


        async def wait_answer(self, cid, fqn, solvepath):
            if DBG:
                print('\tas id %r with tmout=%i' % (cid,self.tmout) )
            unsolved = fqn[len(solvepath) + 1 :]
            tmout = self.tmout // 50

            if unsolved:
                if DBG:
                    print('\twill remain', unsolved)

            solved = None

            while tmout > 0:
                tmout -= 1
                if cid in self.q_return:
                    oid, solved = self.unref(cid)
                    if DBG:
                        print("OID=",oid ,"solved=",solved ,"unsolved=", unsolved)

                    if not undefined(solved):
                        if isinstance(unsolved,str) and len(unsolved):
                            solved = await self.get("%s.%s" % (oid, unsolved), None)
                            unsolved = ''
                            break
                        elif hasattr(solved,'__solved'):
                            if solved.__solved is None:
                                if ADBG:
                                    print("\t?",oid,cid,solved)

                                if isinstance(oid,str) and not oid.startswith('js|'):
                                    solved = oid
                    break

                if DBG:
                    #if not (tmout % 100):
                    print('\tas id %r with tmout=%i solve=%r' % (cid,tmout, cid in self.q_return) )
                await aio.sleep(0.016)
            else:
                print(f"TIMEOUT({self.tmout} ms): wait_answer({cid}) for {fqn}")

            if DBG:
                print('\tas id %r with tmout=%i solved=%r' % (cid,tmout, solved) )

            return solved, unsolved
    # JsProxy

    CallPath.set_proxy(Proxy())
    builtins.window = CallPath().__setup__(None, 'window', [], tip="[ object Window]")
    builtins.document = CallPath().__setup__(None, 'document', [], tip="[ object document]")
    aio.vm = CallPath().__setup__(None, 'vm', [], tip="[ object vm]")


































