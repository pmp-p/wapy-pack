import sys
sys.modules['importlib.abc'] = sys.modules[__name__]
sys.modules['importlib.machinery'] = sys.modules[__name__]


meta_path = []


class MetaPathFinder:
    pass
