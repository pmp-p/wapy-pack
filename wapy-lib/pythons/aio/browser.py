import pythons.aio.plink

# https://developer.mozilla.org/en-US/docs/Web/API/Element/getAttribute
# https://developer.mozilla.org/en-US/docs/Web/API/Element/hasAttribute
# https://developer.mozilla.org/en-US/docs/Web/API/ParentNode/children


#from pythons.aio.plink import window, CallPath, vm
aiovmctl = aio.vm.aio.ctl


CallPath = pythons.aio.plink.CallPath


# https://raw.githubusercontent.com/micropython/micropython-lib/master/socket/socket.py
#
#def _resolve_addr(addr):
#    if isinstance(addr, (bytes, bytearray)):
#        return addr
#    family = _socket.AF_INET
#    if len(addr) != 2:
#        family = _socket.AF_INET6
#    if addr[0] == "":
#        a = "0.0.0.0" if family == _socket.AF_INET else "::"
#    else:
#        a = addr[0]
#    a = getaddrinfo(a, addr[1], family)
#    return a[0][4]
#
#def inet_aton(addr):
#    return inet_pton(AF_INET, addr)
#
#def create_connection(addr, timeout=None, source_address=None):
#    s = socket()
#    #print("Address:", addr)
#    ais = getaddrinfo(addr[0], addr[1])
#    #print("Address infos:", ais)
#    for ai in ais:
#        try:
#            s.connect(ai[4])
#            return s
#        except:
#            pass

#class socket(_socket.socket):
#
#    def accept(self):
#        s, addr = super().accept()
#        addr = _socket.sockaddr(addr)
#        return (s, (_socket.inet_ntop(addr[0], addr[1]), addr[2]))
#
#    def bind(self, addr):
#        return super().bind(_resolve_addr(addr))
#
#    def connect(self, addr):
#        return super().connect(_resolve_addr(addr))
#
#    def sendall(self, *args):
#        return self.send(*args)
#
#    def sendto(self, data, addr):
#        return super().sendto(data, _resolve_addr(addr))

class socket:

    _GLOBAL_DEFAULT_TIMEOUT = 30
#    IPPROTO_IP = 0
#    IP_ADD_MEMBERSHIP = 35
#    IP_DROP_MEMBERSHIP = 36
#    INADDR_ANY = 0
#    error = OSError


    def __init__(self):

        self.sid = -1
        self.size = -1

        self.peek = 0
        self.tell = 0
        self.closed = None
        self.port = -1
        self.iface = ""
        self.tmout = self._GLOBAL_DEFAULT_TIMEOUT
        self.clients = {}

    @classmethod
    def getaddrinfo(cls, host, port):
        return [ [(host,port,)] ]


    def addEventListener(self, ev, cb):
        self.clients.setdefault( ev, [] ).append(cb)

    def makefile(self):pass

    def write(self,b):
        CallPath.proxy.io( self.sid ,m="N", jscmd=b )

    def __repr__(self):
        return "(socket)#{}".format( self.sid )

    def fileno(self):
        return str(self.sid)

    def __bool__(self):
        return (not self.closed) and (int(self.sid) > 0)

    def bind(self,addr):
        self.iface, self.port = addr
        return self

    async def async_listen(self):
        self.sid = await aiovmctl.bind(self.iface, self.port)
        return self

    def listen(self):
        aio.await_for( self.async_listen() , 3 )
        aio.fds[self.fileno()] = self
        self.closed = False
        # ready to accept

    def write(self, data):
        return aio_write(self.fileno(), data)

    async def set_open(self,tmout):

        # register as a valid FD consummer into fd queue
        aio.fds[self.fileno()] = self
        self.closed = False
        result = await aio.ctl(self, 'open', tmout * 1_000)

        if isinstance(result, Exception):
            self.closed = True
            raise result

        return self

    async def async_accept(self, filter):
        s = self.__class__()
        s.sid = await aiovmctl.accept(filter)
        result = await s.set_open(self.tmout)
        await aiovmctl.connect(s.fileno())
        return result

    async def connect(self, addr, tmout):
        self.sid = await aiovmctl.open_ws(*addr)
        return await self.set_open(tmout)

    def accept(self):
        accepted = undef
        filter = ""
        # invalid socket opening returns undef sentinel
        while accepted is undef:
            while not aio_return(self):
                aio_suspend()
            filter = self.read(0)
            accepted = aio.await_for(self.async_accept(filter), self.tmout)
        accepted.vaddr = filter
        return accepted, filter


    def read(self, max):
        # TODO read max
        data = aio_read(self.sid, max)
        ld = len(data)
        self.peek  -= ld
        self.tell += ld
        return data


    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        pdb("113: N/I socket.close()")


socket.socket = socket
builtins.socket = socket
sys.modules["socket"] = socket

def aio_read(fd, max):
    return aio.fds.pop('#%s' % fd , '' )
builtins.aio_read = aio_read

def aio_open(url, mode, tmout):
    sock = socket()
    host, port = url.rsplit(':',1)
    port = int(port)

    coro = sock.connect( (host,port,), tmout )
    if aio.ctx:
        return coro

    print("sync aio_*", aio.ctx)
    return aio.await_for( coro, tmout )
#    aio.fsync( sock ,  coro, tmout )
#    return sock


builtins.aio_open = aio_open


def aio_return(obj):
    if obj.peek > 0:
        return True
    import aio_suspend
    return obj.peek > 0

builtins.aio_return = aio_return




def aio_write(fd, data):
    aiovmctl.write(fd,data)
    aio.vm.finalize

builtins.aio_write = aio_write


