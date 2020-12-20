import struct
import embed

CONST = lambda x:x
print('4:#FIXME: parser and const!')

# C/C++ compiler dependant
NULLPT_SIZE = CONST(4)

if __UPY__:
    import uctypes as this
    if __WASM__:
        PT_SIZE = CONST(4)
    else:
        PT_SIZE = CONST(8)
else:
    # would crash wapy-micropython but not wapy-pycopy
    # from micropython import const

    # https://github.com/pfalcon/pycopy-lib/blob/master/cpython-uctypes/uctypes.py
    import ctypes as this

    def bytearray_at(addr, sz):
        # TODO: Currently just copies contents as bytes, not mutable inplace
        return this.string_at(addr, sz)

    this.VOID    = 0
    this.UINT8   = 0
    this.USHORT  = 268435456
    this.INT8    = 134217728
    this.INT16   = 402653184
    this.UINT16  = 268435456
    this.UINT32  = 536870912
    this.INT32   = 671088640
    this.INT64   = 939524096
    this.UINT64  = 805306368
    this.FLOAT32 =-268435456
    this.FLOAT64 =-134217728
    this.PTR     = 536870912
    this.INT     = 671088640

    if len(struct.pack("N",0))==4:
        PT_SIZE = CONST(4)
    if len(struct.pack("N",0))==8:
        PT_SIZE = CONST(8)




# todo CFUNCTYPE should not be some prototype wrapper but a named function
# eg _sdlsize = CFUNCTYPE(Sint64, POINTER(SDL_RWopsBase)) should be :
# @ffi_cfunc
# def _sdlsize(Sint64, POINTER(SDL_RWopsBase)):
#   pass
# that needs pre-processing .py

try:
    DBG = "ctypes" in DBG
except:
    DBG = 0


def __getattr__(attr):
    global this
    return getattr(this, attr)


def pointer(v):
    return struct.pack("P", v)


class PTYPE(str):
    pass


# TODO work on storage classes not instances

def sizeof(cstruct, setval=0, v=0):
    if isinstance(cstruct, tuple):
        if isinstance(cstruct[0], tuple):
            cumul = 0
            for arg in cstruct:
                argsize = sizeof(arg)
                if not argsize:
                    raise Exception("invalid struct")
                cumul += argsize
            return cumul
        return abs(cstruct[1])

    try:
        # while this could be a class
        if cstruct == type(None):
            if v:
                print(cstruct, "is None")
            return 0

        if issubclass(cstruct, str):
            if not issubclass(cstruct, PTYPE):
                raise Exception("%r is not PTYPE storage class but %r" % (cstruct, cstruct))

            # can only be a POINTER()
            setval = PT_SIZE
            cname = cstruct.__name__
        else:
            sz = PT.sizeof(cstruct)
            if sz:
                return sz
            cname = cstruct.__name__
    except TypeError:
        # or we have an instance

        if isinstance(cstruct, CFUNCTYPE):
            return PT_SIZE

        if isinstance(cstruct, tuple):
            if v: print(cstruct, "is tuple")
            return 0

        if isinstance(cstruct, str):
            if not isinstance(cstruct, PTYPE):
                raise Exception("%r is not PTYPE instance but %r" % (cstruct, cstruct.__class__))

            # can only be a POINTER()
            setval = PT_SIZE
            cname = str(cstruct)


    st = Structure.cstructs.setdefault(cname, {})
    sz = st.setdefault("struct", setval)
    if not sz and setval:
        st["struct"] = setval
    return sz

# BUG
# ctypes.ancestors( ctypes.c_void_p )

def ancestors(c):
    scanned = [c]
    to_scan = list(c.__bases__)
    while len(to_scan):
        e = to_scan.pop()
        if not e in scanned:
            scanned.append(e)
        #print("bases:",to_scan," Scanned",scanned)
        #print("scanning",e,'for',e.__bases__)
        subscan = list(e.__bases__)
        while len(subscan):
            b = subscan.pop()
            if b in scanned:
                continue
            if b in to_scan:
                continue
            #print(" sub-base:", b )
            to_scan.append(b)
            #aio.suspend()
    return scanned

def struct_size_get(cstruct, verbose=0):
    cumul = sizeof(cstruct)
    if cumul:
        return cumul

    # pointer only ?
    if not hasattr(cstruct, "_fields_"):
        try:
            if issubclass(cstruct, (PT, c_void_p, PTYPE) ):
                return sizeof(cstruct, setval=PT_SIZE)

            if PT in ancestors(cstruct):
                return sizeof(cstruct, setval=PT_SIZE)
            isc = True
        except TypeError:
            if isinstance(cstruct, (PT, PTYPE) ):
                return sizeof(cstruct, setval=PT_SIZE)
            isc = False
        if isc:
            raise Exception("class {} with no storage field is not storage derived {}".format(cstruct, ancestors(cstruct)))
        else:
            raise Exception("instance {} with no storage field has no storage class {}".format(cstruct, cstruct.__class__))


    # walk was not complete
    if verbose:
        print(cstruct.__name__)
    for (fname, ftype) in cstruct._fields_:
        if verbose:
            print("  ", fname, end=" -> ")
        sz = sizeof(ftype)
        if not sz:
            sz = sizeof(ftype, v=1)
            if verbose:
                print("N/A {}".format(repr(ftype)), sizeof(ftype, v=1))
            break
        cumul += sz
        if verbose:
            print(sz)
    else:
        return sizeof(cstruct, setval=cumul)
    return 0

if __UPY__:
    def struct_field_get(cstruct, instance, verbose=0):
        pstruct = {}
        offset = 0
        sz = 0
        # minimal type is raw pointer, do not handle
    #    if not hasattr(cstruct,'_fields_'):
    #        print("------ pointer ? --------")
        for (fname, ftype) in cstruct._fields_:
            offset += sz
            if verbose:
                print("  ", fname, end=" -> ")
            sz = sizeof(ftype)
            if not sz:
                print("N/A {}".format(repr(ftype)), sizeof(ftype, v=1))
                raise Exception("Storage size of '{}' unknown".format(cstruct.__name__))

            if isinstance(ftype, tuple):
                # ok, not a sub structure
                if not isinstance(ftype[2], tuple):
                    if verbose:
                        print(ftype[0], "@", offset)
                    pstruct[fname] = ftype[2] | offset
                    continue

            # it is a union or padding
            if verbose:
                print("?(", ftype, ")[", sz, "]@", offset)
            pstruct[fname] = (this.PTR | offset, this.UINT8)

        return pstruct
else:

    def struct_field_get(cstruct, instance, attr, verbose=1):
        pstruct = {}
        offset = 0
        sz = 0
        for (fname, ftype) in cstruct._fields_:
            offset += sz
            if verbose:
                print("  ", fname, end=" -> ")
            sz = sizeof(ftype)
            if not sz:
                print("N/A {}".format(repr(ftype)), sizeof(ftype, v=1))
                raise Exception("Storage size of '{}' unknown".format(cstruct.__name__))

            if isinstance(ftype, tuple):
                # ok, not a sub structure
                if not isinstance(ftype[2], tuple):
                    ctyp = ctypes_binder.ffi.DynMod.typemap[ftype[0]]
                    if verbose:
                        print( ftype[0], "@", offset,  )

                    pstruct[fname] = ( offset , ctyp )
                    if fname==attr:
                        break
                    continue

            # it is a union or padding
            print("?(", ftype, ")[", sz, "]@", offset)
            pstruct[fname] = (this.PTR | offset, this.UINT8)
            if fname==attr:
                break
        return pstruct


class CSpace:
    def __init__(self, cptr, iptr):
        self.ptr = cptr
        if __UPY__:
            self.ref = 0
        else:
            self.ref = struct.pack('P', 0 )

        self.type = iptr
        self.val = undefined
        self.size = PT_SIZE


class PT:
    types = {}

    # could speed up struct_size_get() on PT subclasses
    #_fields_ = ( ("c.ptr",("p", 4, this.PTR),) )

    @staticmethod
    def sizeof(cls):
        return ffisign.get(cls, (0, 0,))[1]

    def __init__(self, iptr=PTYPE("void"), cptr=-1):
        c = CSpace(cptr, iptr)
        self.__c = c
        #  by default is Invalid pointer  addr 0 size 4
        if not isinstance(iptr, PTYPE):
            c.size = sizeof(iptr)

            if isinstance(iptr, type(PT)):
                struct_size_get(iptr)
                iptr = iptr.__name__

            if not isinstance(iptr, str):
                # raw pointer ? should not use that ...
                print("44:warning raw pointer")
                c.ptr = iptr


    def __int__(self):
        c = self.__c
        if not c.ref and (c.ptr < 0):
            raise Exception("Pointer address not set")

        # TODO this only handle const ptr
        if c.ptr<=0:
            print("310:",self.__name__, c.size, c.ref )
            c.ptr = struct.unpack("P", c.ref)[0]

        return c.ptr

    value = __int__

    def __add__(self, v):
        return int(self) + (v * self.__c.size)

    def byref(self):

        c = self.__c
        if not c.ref:
            if c.ptr < 0:
                c.ptr = 0

            if c.size == PT_SIZE:
                c.ref = struct.pack("P", c.ptr)
            else:
                if c.size > 0:
                    sz = c.size
                else:
                    sz = sizeof(c.type)
                c.ref = struct.pack("{}B".format(sz), *((0,)*sz ))

            # embed.log("# byref ref=%s ptr=%s" % (self.__c.ref, self.__c.ptr))
        return c.ref

    if __UPY__:
        def __getattr__(self, attr):
            if attr == '__c':
                return self.__c

            if attr[0]=='_':
                return

            c = self.__c
            if c.val is undefined:
                print("__getattr__",attr)
                pstruct = struct_field_get(c.type, self)
                print("ctype.cast",pstruct)
                c.val = this.struct(this.addressof(c.ref), pstruct)
            return getattr(c.val, attr)
    else:
        # cpython ctypes does not have uctypes.struct(addr, descriptor, layout_type=NATIVE)
        def __getattr__(self, attr):
            if attr == '__c':
                return self.__c
            c = self.__c
            addr = int(self)
            offset, ctyp = struct_field_get(c.type, self, attr)[attr]
            addr += offset
            return ctyp(addr).value


    def __repr__(self):
        c = self.__c
        try:
            if not c.ref:
                if c.ptr < 0:
                    return "^nullptr"
        except AttributeError:
            return "%s is not an instance" % object.__repr__(self)

        return "^{}".format(self.__int__())


def POINTER(ctype):
    if isinstance(ctype, tuple):
        sign = ctype[0]
        sz = ctype[1]
        cname = "{}{}".format(sign, sz)
    else:
        # a POINTER() ?
        sz = 4
        sign = "P"
        if isinstance(ctype, str):
            cname = str(ctype)
        else:
            # a Structure
            cname = ctype.__name__

    if not cname in PT.types:
        c = PTYPE(cname)
        ffisign[c] = (sign, sz, this.PTR)
        PT.types[cname] = c
    return PT.types[cname]


class c_void_p(PT):
    if __UPY__:
        pass
    else:
        in_dll = this.c_void_p.in_dll

class c_char_p(PT):
    pass


class Structure(PT):

    cstructs = {}


py_object = "py_object"





c_null = ("v", NULLPT_SIZE, this.VOID)
c_char = ("c", 1, this.USHORT)
c_uint8 = ("B", 1, this.UINT8)
c_int8 = ("b", -1, this.INT8)
c_uint16 = ("H", 2, this.UINT16)
c_int16 = ("H", -2, this.INT16)
c_uint32 = c_uint = ("I", 4, this.UINT32)
c_int32 = c_int = ("i", -4, this.INT32)

c_size_t = ("N", 4)

c_ulong = c_ulonglong = c_uint64 = ("Q", 8, this.UINT64)

c_long = ("q", -8, this.INT64)
c_longlong = ("q", -8, this.INT64)
c_int64 = ("q", -8, this.INT64)

c_float = ("f", -4, this.FLOAT32)
c_double = ("f", -8, this.FLOAT64)

ffisign = {
    type(None): ("v", NULLPT_SIZE, this.VOID),
    c_null: ("v", NULLPT_SIZE, this.VOID),
#    c_void_p: ("p", 4, this.PTR),
    c_void_p: ("p", PT_SIZE, this.PTR),
#   c_char_p: ("s", 4, this.PTR),
    c_char_p: ("s", PT_SIZE, this.PTR),
    int: ("i", 4, this.INT),
    float: ("f", 4, this.FLOAT32),
#    double: ("d", 8, this.FLOAT64),
}
print("457:#FIXME:detect double build for floats")

if __UPY__:

    class CFUNCTYPE:
        __name__ = "CFUNCTYPE"

        def __init__(self, *argv, **kw):
            self.argv = argv
else:
    pdb("459: CFUNCTYPE")
    CFUNCTYPE = this.CFUNCTYPE


def memmove(*argv, **kw):
    print("memmove", argv, kw)
    raise Exception("N/I")


def string_at(*argv, **kw):
    print("string_at", argv, kw)
    raise Exception("N/I")


class Union:
    _fields_ = []


def _Pointer(*argv, **kw):
    print("_Pointer", argv, kw)
    raise Exception("N/I")


def convstack(fn, argv, kw):
    argv = list(argv)
    for i, arg in enumerate(argv):
        if isinstance(arg, PT):
            argv[i] = arg.__c.ptr
    return argv, kw

class unbound:
    def __init__(self,name):
        self.__name__ = name

    def __call__(self, *argv, **kw):
        pdb("419: unbound",self, argv,kw)

    def __repr__(self):
        return self.__name__

class ctypes_binder:
    def __init__(self, lib):
        import ffi
        ctypes_binder.ffi = ffi

        self.name = lib
        if sys.platform == "wasm" and lib=='libsdl2.so':
            pdb("386:ffi SDL2 static workaround")
            self.lib = ffi.open(None)
        else:
            self.lib = ffi.open(lib)

    def __call__(self, funcname, *argv, **kw):
        ret = c_null

        if len(argv) == 1:
            argv = argv[0]
        elif len(argv) == 2:
            argv, ret = argv
        else:
            argv = ()

        # fix "v"
        if ret is None:
            ret = c_null

        # fix ()
        if argv is None:
            argv = (c_null,)

        ffidef = ffisign.get(ret, ret)

        # is it a struct ?
        if not isinstance(ffidef, tuple):
            # print(ffidef, ret, "*", funcname, argv)
            ret_sig = "P"
        else:
            ret_sig = ffidef[0]

        try:
            sig = [ret_sig, funcname, "".join([ffisign.get(c, c)[0] for c in argv])]
            if ret_sig != "N":
                try:
                    dllcall = self.lib.func(*sig)
                except TypeError as e:
                    print("462:", *sig)
                    sys.print_exception(e, sys.stderr)
                    dllcall = unbound(funcname)

                if not isinstance(ret, tuple):

                    # pointer wrapping class
                    if isinstance(ret, str):

                        def func(*argv, **kw):
                            argv, kw = convstack(funcname, argv, kw)
                            return PT(ret, dllcall(*argv, **kw))

                        return func
                    embed.log("fn '%s' does not return ptr on specific type : %s" % (funcname, ret))

                def func(*argv, **kw):
                    argv, kw = convstack(funcname, argv, kw)
                    return dllcall(*argv, **kw)

                return func
            else:
                if DBG:
                    print(" - unsupported ffi mapping :", ret_sig, *sig)
        except OSError:
                pdb("444:ctypes: no ffi match for %s in %s" % (funcname, self.name))
        except TypeError as e:
            if DBG or not __UPY__:
                print()
                print(" - unsupported call type -", e, ret, "*", funcname, argv)



def static(c_n):
    return PT(c_n)
