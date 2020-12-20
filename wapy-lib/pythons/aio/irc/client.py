
class client:
    OFFLINE = True

    def __init__(self,ip,port,ssl='',**kw):
        if ssl:ssl='s'

        set = kw.setdefault

        self.channels = set('channels',[])

        set('url', f'ws{ssl}://{ip}:{20000+int(port)}' )

        self.nick = set('nick',"aio_irc_client")
        if not __UPY__:
            self.nicks =   set('nicks',[self.nick,f"{self.nick}_",f"{self.nick}__"])
            self.current = 0
            self.nick = self.nicks[self.current]
        self.state = kw

    async def handler(self, cmd):
        print("20:",__file__,'default_handler>',*cmd)
        return False


    def send(self, data):
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        data = data + "\r\n"
        self.ws.send_binary(data.encode("utf-8"))

    async def run(self):
        hi = False
        self.instance = self
        self.ws = aio.websocket( self.state['url'] )

        for event in self.ws.connect(poll=.010):
            case = event.name
            if case == 'poll':
                await aio.sleep_ms(.016)
                continue

            if case == 'binary':
                data = event.data.decode()
                if data[0] != ":":
                    if data.startswith('PING :'):
                        self.send(data.strip().replace('PING ','PONG ',1))
                    else:
                        pdb("49:",__file__,'srv?', data)
                    continue

                if not await self.handler( data.split(' ') ):
                    pdb("49:",__file__,'IRC?', data)

                continue

            # deprecated with websockify
            if case == 'text':
                print("56:TEXT>",event.text)
                continue

            if case == 'pong':
                continue

            if case == 'connecting':
                continue

            if case == 'connected':
                continue

            if case == 'closing':
                continue

            if case == 'disconnected':
                continue

            if case == 'ready':
                client.OFFLINE = False
                for cmd in (
                    "CAP LS",
                    "NICK {}".format((self.nick)),
                    "USER {} {} local :wsocket".format((self.nick), (self.nick)),
                ):
                    self.send(cmd)

                if not hi:
                    for channel in self.state['channels']:
                        self.send(f'JOIN {channel}')
                    hi=True

                continue
            if case == 'connect_fail':
                pdb(f"60:maybe could be missing 'android.permission.INTERNET' cap {self.state} ?")
                break
            pdb("74: event.name?",case)
            if not aio.loop:
                break
