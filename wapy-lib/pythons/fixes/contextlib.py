
old = print
class redirect_stdout:


    def __init__(self,file=None):
        self.out = file or __import__('uio').StringIO()

    def print(self,*a,**k):
        global old
        if not 'file' in k:
            k['file']=self.out
        return old(*a,**k)

    def __enter__(self,*a,**k):
        setattr(builtins,'print', self.print )
        return self

    def getvalue(self):
        try:
            return self.out.getvalue()
        finally:
            self.out.close()
            del self.out
    __str__ = getvalue

    def __exit__(self,*a,**k):
        delattr(builtins,'print')
