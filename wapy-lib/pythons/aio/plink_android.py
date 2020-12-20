from .plink import BaseProxy, CallPath

ADBG=DBG=1

def dumps(data):
    import json
    res = json.dumps(data)
    print(res)
    return res


class AndroidProxy(BaseProxy):

    # assume everything is UI thread related

    ui = True


    def __init__(self):
        self.caller_id = 0
        self.tmout = 800 # ms
        self.cache = {}
        aio.DBG=1
        self.q_return = aio.q  # {}
        self.q_req = aio.req # []

        self.q_reply = []
        self.q_sync = []

        self.q_async = []
        self.q_ui = self.q_async

    def unref(self, cid):
        if cid in self.q_req:
            self.q_req.remove(cid)
        else:
            print('315: %s was never awaited'%cid)
        oid = self.q_return.pop(cid)
        try:
            oid = oid[0]
            otype, ocn, optr = oid.split(':',2)
            if otype == 'p':
                tip = f"<RMI...{ocn.rsplit('.',1)[-1]}@{optr}>"
                if ADBG:print("UNREF:60:", cid, tip, otype, ocn, optr)

                if not oid in self.cache:
                    if ADBG:print("63:creating a new pipeline for the ref object")
                    self.cache[oid] = CallPath().__setup__(None, oid, [], tip=tip)
                return oid, self.cache[oid]

            if otype in 'isbfd':
                if ocn=='str':
                    return oid, str(optr)
                if ocn=='int':
                    return oid, int(optr)
                if ocn=='float':
                    return oid, float(optr)
                if ocn=='bytes':
                    return oid, optr.encode('utf-8')
                print("ERROR:UNREF:51: invalid python class type", otype, ocn, optr )
        except Exception as e:
            print("ERROR:UNREF:66:",oid,e)
            sys.print_exception(e)
            raise
        # type 'v' void/null
        return oid, None


    # act will discard results, if results are needed you MUST use await
    def act(self, cp, c_argv, c_kw, **kw):
        cid = self.new_call()
        self.q_req.append(cid)

        cn, meth = cp.rsplit('.',1)

        # java classes like eg "android.widget.RelativeLayout$LayoutParams"
        cn = cn.replace('__','$')

        if cn[1]==':':
            pdb("71 .act(2):",cn,meth)
            #instance method call
            ct = 2
        #ctor
        elif meth == 'newInstance':
            ct = 0
        #static/classmethod calls
        else:
            pdb("79 .act(1):",cn,meth)
            ct = 1

        # IO
        call = [int(cid), ct, cn, meth ]
        r_argv = []
        for argv in c_argv:
            if  isinstance(argv, CallPath):
                r_argv.append( str(argv) )
            else:
                r_argv.append( argv )
        call.extend(r_argv)
        self.q_async.append( call )
        return cid

    async def get(self, cp, argv, **kw):
        cid = self.act(cp,argv,**kw)
        while True:
            if self.q_return:
                if cid in self.q_return:
                    self.q_req.remove(cid)
                    return self.q_return.pop(cid)
            await aio.sleep_ms(1)


#    def io(self, cid, raw=None, m=None, jscmd=None):
#        if jscmd:
#            print("\n  >> js io=",cid, jscmd)
#            #jscmd = binascii.hexlify( jscmd.encode('utf-8') ).decode('utf-8')
#            #sys.__stdout__.write( 'TODO: {"dom-%s":{"id":"%s","m":"//%c:%s"}}\n' % (cid, cid,m, jscmd) )
#        elif raw:
#            print("\n  >> rawio=",cid, raw)
#            #sys.__stdout__.write( raw )
#        return cid




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




    async def wait_answer(self, cid, fqn, solvepath):
        if DBG:
            print('\tas id %s' % cid)
        unsolved = fqn[len(solvepath) + 1 :]
        tmout = self.tmout
        if unsolved:
            if DBG:
                print('\twill remain', unsolved)

        solved = None

        while tmout > 0:
            if cid in self.q_return:
                oid, solved = self.unref(cid)
                if DBG:
                    print("OID=",oid,"solved=",solved)

                if len(unsolved):
                    solved = await self.get("%s.%s" % (oid, unsolved), None)
                    unsolved = ''
                    break

                if isinstance(solved, CallPath):
                    if solved.__solved is None:
                        if ADBG:
                            print("\t?",oid,cid,solved)
#TODO: check all cases for android
                        if isinstance(oid,str) and not oid.startswith('js|'):
                            solved = oid

                break
            await aio.sleep_ms(1)
            tmout -= 1
        else:
            print(f"TIMEOUT({self.tmout} ms): wait_answer({cid}) for {fqn}")
        return solved, unsolved
