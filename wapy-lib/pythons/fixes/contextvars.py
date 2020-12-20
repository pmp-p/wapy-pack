if __UPY__:
    this = __import__(__name__)

    class LookupError(Exception):pass

    class ContextVar:
        def __init__(self, name, default=this):
            self.name = name
            ctx = getattr(this,name,this)
            if ctx is this:
                if default is not this:
                    self.default = default
                    pdb("10: contextvars +{}".format(name))
                    self.set(default)
                else:
                    pdb("13: contextvars lookup {}".format(name))
    #        else:
    #            pdb("13: contextvars access {}={}".format(name,ctx))


        def set(self,v):
            setattr(this,self.name,v)


        def get(self,default=this):
            if default is this:
                try:
                    default = self.default
                except:pass

            try:
                return getattr( this, self.name )
            except AttributeError:
                raise LookupError(self)
    #FIXME: LookupError
else:
    raise Exception('contextvars')
