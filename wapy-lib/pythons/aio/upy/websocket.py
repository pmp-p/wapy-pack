class evt:
    name = ''

class websocket:
    def __init__(self, url, **kw):
        pdb(f"3: EXP async websocket provider {url}")

    def connect(self, poll=0):
        while not aio.loop.is_closed():
            evt.name = 'poll'
            yield evt
