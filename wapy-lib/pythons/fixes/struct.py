import ustruct as self
def __getattr__(attr):
    return getattr(self,attr)
