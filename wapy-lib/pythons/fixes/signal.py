

SIG_DFL = 0
SIG_IGN = 1

SIGINT = 2
SIGPIPE = 13
SIGTERM = 15

def default_int_handler(unused_signum, unused_frame):
    pass

def signal(n, handler):
    def fake_signal(*argv,**kw):
        print(signal,n,handler)
    return fake_signal

sys.modules['_signal'] = sys.modules[__name__]
