import os, shutil

rom = [
    "ffilib.py: ffilib/ffilib.py",
    "pyreadline.py: readline/pyreadline.py",
    "stat.py: stat/stat.py",
    "types.py: types/types.py",
    "datetime.py: datetime/datetime.py",
    "html: html/html",
    "importlib.py: importlib/importlib.py",
    "imp.py: imp/imp.py",
    "pythons: pythons",
    "wapy_wasm_site.py: site/wapy_wasm_site.py",
    "zipfile.py: zipfile/zipfile.py",
    "collections: collections/collections",
    "collections/defaultdict.py: collections.defaultdict/collections/defaultdict.py",
    "collections/deque.py: collections.deque/collections/deque.py",
]

sources_dir = ('/data/git/wapy-pack/wapy-lib','/data/git/pycopy-lib',)

for mod in rom:
    target, src = mod.split(': ')
    if target.endswith('.py'):
        for root in sources_dir:
            maybe = f'{root}/{src}'
            if os.path.isfile(maybe):
                print(f'{maybe} -> {target}')
                shutil.copyfile(maybe,f'rom/{target}')
                break
        else:
            print("NOT FOUND ! ", src)
    else:
        for root in sources_dir:
            maybe = f'{root}/{src}'
            print(maybe)
            if os.path.isdir(maybe):
                destdir = f'rom/{target}'
                print(f'{maybe} -> {destdir}')
                if os.path.isdir(destdir):
                    shutil.rmtree(destdir)
                os.system(f'cp -r {maybe} {destdir}')
                break
        else:
            print("NOT FOUND ! ", src)
