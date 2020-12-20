# upython
if __UPY__:
    #
    print('NB: this module [',__name__,'] requires the scheduler repl patch for unix port to be compiled in',file=sys.stderr)
    #
    import micropython
    self = micropython


    tasks = []
    def __getattr__(attr):
        return getattr(self,attr)


    def scheduler():
        global tasks
        lq = len(tasks)
        while lq:
            fn,arg = tasks.pop(0)
            fn(arg)
            lq-=1

    def schedule(fn,arg):
        global tasks
        assert callable(fn)
        assert isinstance(arg,int)
        tasks.append( (fn,arg,) )


    def mem_info():
        return """mem: total=?, current=?, peak=?
    stack: ? out of ?
    GC: total: ?, used: ?, free: ?
     No. of 1-blocks: ?, 2-blocks: ?, max blk sz: ?, max free sz: ?"""

# cpython
else:
    # https://github.com/pfalcon/pycopy-lib/blob/master/cpython-micropython/micropython.py



    def native(x):
        return x

    def viper(x):
        return x


    # Override standard CPython modules/builtins with Pycopy semantics

    import builtins

    try:
        import uio
        builtins.open = uio.open
    except:
        pdb("cpython-uio not found", __import__('sys').path)



    import gc

    def mem_free():
        return 1000000

    def mem_alloc():
        return 1000000

    gc.mem_free = mem_free
    gc.mem_alloc = mem_alloc
