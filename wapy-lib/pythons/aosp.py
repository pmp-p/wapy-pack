# pythons android support for flavours that implement sys.getandroidapilevel

if not __UPY__:
    import sys

    todel = []
    for i, elem in enumerate(sys.path):
        if elem.startswith('/data/data/'):
            todel.append(i)

    while len(todel):
        sys.path.pop( todel.pop() )


    # may only works for root shell access
    # sys.path.insert(0,"/data/data/{{ cookiecutter.bundle }}.{{ cookiecutter.module_name }}/usr/lib/python{{ cookiecutter.pyver }}/lib-dynload")

    # so use importlib

    import importlib
    import importlib.abc
    import importlib.machinery

    import sysconfig
    SOABI = sysconfig.get_config_vars('SOABI')[0]


    class ApkLibFinder(importlib.abc.MetaPathFinder):

        @classmethod
        def invalidate_caches(cls):
            pass

        @classmethod
        def find_spec(cls, name, path=None, target=None):
            global SOABI
            for lib in (
                    f"{os.environ['DYLD']}/lib.{name}.{SOABI}.so",
                    f"{os.environ['DYLD']}/lib.{name}.so" ,
                ):
                try:
                    os.stat(lib)
                    pdb(f"ApkLibFinder found : {lib}")
                    loader = importlib.machinery.ExtensionFileLoader(name, path)
                    return importlib.machinery.ModuleSpec(name=name, loader=loader, origin=lib)
                except FileNotFoundError:
                    continue
            pdb(f"ApkLibFinder NOT found : {name}")
            return None

    sys.meta_path.append(ApkLibFinder)
