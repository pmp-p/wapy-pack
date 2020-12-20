import _zipfile
# https://docs.python.org/3/library/zipfile.html?highlight=zipfile#zipfile.ZipFile
# (file, mode='r', compression=ZIP_STORED, allowZip64=True, compresslevel=None, *, strict_timestamps=True)

def ZipFile(file, mode='r', compression=0, allowZip64=True, compresslevel=None, *, strict_timestamps=True):
    zf = _zipfile.ZipFile()
    zf.init(file)
    return zf

# usage : no autodetection of zip archives in sys.path yet, just pattern matching
# from file paths against a zip set ( imp.zipimports = [] )

# import imp
# zf = ZipFile('/data/git/wapy-lib-pack/wapy.zip')

# import sys
# sys.path.append('/data/git/wapy-lib-pack/wapy.zip/assets/lib/python3')
# imp.zipimports.append( zf )

