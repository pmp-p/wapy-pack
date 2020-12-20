import sys, typing

#BAD: does not handle multilines if C could do it somehow
def indent(n,t):
    lt = []
    for l in t.split('\n'):
        lt.append( ' '*n + l)
    return '\n'.join(lt)

#BAD but does the job
def str_default(val):
    val = str(val)
    if val[0]=="'":
        val = '"%s"' % val.strip('\'"')
    return val

def read_init(IDX, T, name, V):
    def make_init(decl, vget, vdef):
        return f"""
    {decl}; // {(T,name,V,)}
    if (argc>{IDX}) {{ {name} = {vget}; }} else {{ {name} = {vdef}; }}
"""

    if T in ['void *']:
        if V in (None,):
            return f"""
    void (*{name})(void); // {(T,name,V,)}
    if (argc>{IDX}) {{ {name} = (void*)argv[{IDX}] ; }} else {{ {name} = &null_pointer_exception; }}
"""

    if T in ['int']:
            return f"""
    int {name}; // {(T,name,V,)}
    if (argc>{IDX}) {{ {name} = mp_obj_get_{T}(argv[{IDX}]); }} else {{ {name} = {V} ; }}
"""

    if T in ['float','double']:
        T = "double"
        return f"""
    double {name}; // {(T,name,V,)}
    if (argc>{IDX}) {{ {name} = mp_obj_get_{T}(argv[{IDX}]); }} else {{ {name} = {V} ; }}
"""


    if T in ['pstr']:
        val = str_default(V)
        return make_init(
            f'mp_obj_t * {name}',
            f'(mp_obj_t*)argv[{IDX}]',
            f'MP_OBJ_NEW_QSTR(qstr_from_str({val},{len(val)-2}))',
        )

    if T in ['str', 'cstr','const char *']:
        val = str_default(V)
        return make_init(
            f'const char *{name}',
            f'mp_obj_str_get_str(argv[{IDX}])',
            f'mp_obj_new_str_via_qstr({val},{len(val)-2})',
        )

    V = 'NULL';
    return f"""
    {T} {name}; // {(T,name,V,)}
    if (argc>{IDX}) {{ {name} = ({T})argv[{IDX}]; }}
    else {{ {name} = {V} ; }}
"""



def is_prepro(line):
    if line.startswith('#if '):
        return True
    if line.startswith('#ifdef '):
        return True
    if line.startswith('#ifndef '):
        return True
    if line.startswith('#error '):
        return True
    if line.startswith('#warning '):
        return True
    if line.startswith('#pragma '):
        return True
    if line.startswith('#else'):
        return True
    if line.startswith('#endif'):
        return True
    if line.startswith('#include '):
        return True
    if line.startswith('#define '):
        return True


def make_c_type(tc, default=None):

    if isinstance(tc,typing.TypeVar):
        tc=repr(tc)
    elif isinstance(tc, str):
        pass
    else:
        tc = tc.__name__

    if tc[0]=='~':
        tc = tc [1:]

    tc = tc.replace('const_char','const char')

    if tc.endswith('_p'):
        tc = tc[:-2]+' *'

        if tc != 'const char *':
            default = 'NULL'

    if tc=='ptr':
        tc='mp_obj_t'
        default = 'mp_const_none'

    if default is None and tc.find('int')>=0:
        default = 0

    return tc, default

def cvar_any(name, obj ):
    init_line = ''
    if isinstance(obj, str):
        decl = f'    {obj} {name};'
    else:
        if isinstance(obj, tuple):
            tc, defv = make_c_type( obj[0], obj[1] )
            decl = f'    {tc} {name};'
            init_line = f'    self->{name} = {defv};'
        else:
            decl=f'//?    {name} {repr(obj)};'
    return decl, init_line

def annotation_rt(ann):
    # ann.__name__
    prefix = 'STATIC mp_obj_t '

    tc, defv = make_c_type(ann)

    tp = tc



# TODO: use mp_types
    if tc in ('dict',):
        tc = 'mp_obj_dict_t *'

    # FIXME _int_from_ conversions
    elif tc in ('int','long','unsigned long'):
        tp = 'int'
        tc = 'long'

    elif tc in ('float','double'):
        tp = 'double'

    elif tc in ('bytes',):
        tc = 'char *'
        tp = 'bytes'
        defv = '(char *)nullbytes'

    elif tc in ('str','pstr'):
        tc = 'const char *'
        tp = 'qstr'

    # unlikely
    elif tc in ('cstr','const_char_p'):
        tc = 'const char *'
        tp = 'str'

    elif tc[0]=='_':
        tp = tc
        tc  = tc.rsplit('_from_',1)[-1]
        if tc=='ptr':
            tc= 'uintptr_t'

    return prefix, tc, tp, defv



def annotation_stack(ann):
    stack = []
    for vname, ctype in ann.items():
        tc, defv = make_c_type( str(ctype) )
        stack.append( f'{tc} {vname}')
    return ', '.join(stack)



def block_from_c_value(prefix, rtp):
    body = []
    if rtp[0]=='_':
        body.append(f'{prefix} mp_obj_new{rtp}(__creturn__);')
    elif rtp == 'int':
        body.append(f'{prefix} mp_obj_new_int(__creturn__);')
    elif rtp == 'bytes':
        body.append(f'{prefix} PyBytes_FromString(__creturn__);')
    elif rtp == 'qstr':
        body.append(f'{prefix} MP_OBJ_NEW_QSTR(qstr_from_str(__creturn__));')
    else:
        body.append(f'{prefix} (mp_obj_t)__creturn__ ;')
    if prefix.count('{')==1:
        return body[-1]+" }"
    return body[-1]


def comment_blocks(in_comment, body, cls, clr, cline):
    # /* */ comments block
    while 1:
        if in_comment:
            if cls.endswith('*/'):
                in_comment = False
                body.append( cline  )
            else:
                body.append("# " + cline)
                break

        if not cls:
            body.append('')
            break

        if cls.startswith('/*'):
            in_comment = True
            body.append( cline  )
            break

        # single line comment
        if cls.startswith('//'):
            body.append( cline  )
            break

        if cls.startswith('#'):
            body.append( '//' + cline[1:]  )

        break

    return in_comment

# TODO: use a proper parser
def self_line(cline):
    #return cline.replace('self.','(*self).')
    return cline.replace('self.','self->')


#=============================================================================
def build_method_code(cfunc, scope, rtc, rtp, fast_ret, with_finally = False):

# TODO:FIXME: this usefull construct is not supported at all
#    def WAPY() -> int:
#    #if  __EMSCRIPTEN__
#        return mp_obj_new_int_from_uint(1);
#    #else
#        return mp_obj_new_int_from_uint(0);
#    #endif
# maybe could be supporting that for whole function body ?

    lblname = 'lreturn__'

    in_comment = False
    in_try = False
    in_return = False
    in_finally = False
    last_indent = 0
    cur_indent = 0
    brace_close = []

    body = []
    if with_finally:
        body.append( '\n    // ------- method body --------' )
    else:
        body.append( '\n    // ------- method body (try/finally) -----' )

    for cline in scope.c:
        if is_prepro(cline.lstrip()):
            body.append( cline  )
            continue

        cline = self_line(cline)

        cls = cline.lstrip()
        clr = cline.rstrip()
        clstrip = cline.strip().replace('  ',' ').replace(' :',':')
        was_comment = in_comment
        in_comment = comment_blocks(in_comment, body, cls, clr, cline)
        if was_comment or in_comment:
            continue


        # code handling

        cur_indent= len(cline) - len(cls)
        if not last_indent:
            last_indent = cur_indent

# TODO: check for comments after ':'
        if clstrip.endswith(':'):
            # TODO: add missing () for  if/while
            for x in ('if','while'):
                if clstrip.startswith(f'{x} '):
                    if not clstrip.startswith(f'{x} ('):
                        cline = cline[:-1].replace(f'{x} ',f'{x} (',1)+'):'

            # transform self. into (*self).  or self->
            # cline = self_line(cline)

            last_indent = cur_indent
            if clstrip =='try:':
                cline = ' ' * cur_indent + '{ //try:'
                in_try = True
            elif clstrip =='finally:':
                # finally blocks are dedents too
                if len(brace_close):
                    body.append(brace_close.pop() )
                    last_indent = cur_indent

                cline = ' ' * cur_indent + '{ //finally:\n'
                cline += ' ' * cur_indent + block_from_c_value("    __preturn__ = ", rtp)
                in_try = False
                in_finally = True
            else:
                cline = cline[:-1] + ' {'
            brace_close.append(  f"{' '*last_indent}}}" )

        else:
            # transform self. into (*self).  or self->
            # cline = self_line(cline)
            if cur_indent > last_indent:
                # indenting, memorize the new block indentation
                last_indent = cur_indent
            elif cur_indent < last_indent:
                # we dedent : close the last block
                if len(brace_close):
                    body.append(brace_close.pop() )
                    last_indent = cur_indent
            else:
                # we are in same indent block
                #TODO: raise if finally
                pass

# TODO: check for end line comments what would be after missing ';'
            if not clr.endswith('([{,"\''):
                cline = clr.rstrip('; ')
                if fast_ret:
                    if cls.startswith('return'):
                        cline = cline.replace('return','goto lreturn__;')
                elif cls.startswith('return '):
                    if in_try:
                        cline = cline.replace('return ',f'__creturn__ = ({rtc})')
                    else:
                        cline = cline.replace('return ',f'{{ __creturn__ = ({rtc})')
                        cline += '; goto lreturn__; }';

                if not cline[-1] in '({,>.;':
                    cline = cline + ';'

        body.append( cline  )

    while len( brace_close ):
        body.append(brace_close.pop())

    if fast_ret:
        body.append("return mp_const_none;")
    elif in_finally:
        # late return final type
        body.append("return __preturn__;")
    else:
        if ''.join(body).find(f'goto {lblname}')>0:
            body.append( block_from_c_value(f'{lblname}: return', rtp) )
        else:
            body.append( block_from_c_value(f'return', rtp) )


    return body

    body.append('}')

    cfunc.extend( body )


#==============================================
def build_method(nscname, decal_stack, scope):
    ann = dict( scope.__annotations__ )

    # treat return value
    c_type = ann.pop('return')
    p_type = ptypes.get(c_type, c_type)
    rt_prefix, rtc, rtp, rt_default = annotation_rt(c_type)

    # input stack : kw and named args not handled atm
    argc = len(ann)+decal_stack
    stack_ann = annotation_stack(ann)

    cfunc = []

    print('    ',nscname,'_',scope.name, decal_stack, )

    opt_preturn = len(cfunc);
    cfunc.append(f'// opt: no finally {rtp} slot')

    fast_ret = 0
    if rt_default is not None:
        cfunc.append(f'    {rtc} __creturn__ = {rt_default};')
    else:
        if  rtc == 'void':
            fast_ret = len(cfunc)
        cfunc.append(f'    {rtc} __creturn__;')

    # toplevel don't use a allocated self, but global module state singleton instead
    if decal_stack>0:
        cfunc.append(f'''
    {nscname}_obj_t *self = ({nscname}_obj_t *)MP_OBJ_TO_PTR(argv[0]);
    (void)self;
''')


    if scope.asyncdef :
        cfunc.append('    // TODO: async : resume with go after last yield ')

# 1+ len(argv), self is implicit at index 0
# this allow simpler conversion from test module code to C class code.
# TODO: what about classmethod 1+len(argv) /staticmethod len(argv) ?

    argv = []
    item_pos = 0

    for item_pos,(k, ptype_vdef) in enumerate( ann.items()):
        ct, vdef = make_c_type(*ptype_vdef)
        if not item_pos:
            cfunc.append(f'    // {scope.header}')
            cfunc.append(f'    // {ptype_vdef} => {ct} = {vdef}')

        cfunc.append( indent(4, read_init(decal_stack+item_pos, ct, k, vdef)) )
        argv.append(k)


    for line in scope.c:
        if line.find('finally')>=0:
            has_finally = True
            break
    else:
        has_finally = False

    if has_finally:
        # add storage for Py type pointer conversion.
        cfunc[opt_preturn] =  f'    mp_obj_t __preturn__;'
        if fast_ret:
            raise Error("FIXME: fast return not compatible with try/finally")
        fast_ret= 0

    if fast_ret:
        cfunc[fast_ret] = '// opt : void return'

    cfunc.extend( build_method_code(cfunc, scope, rtc, rtp, fast_ret, with_finally=has_finally) )
    return argc, c_type, p_type, '\n'.join(cfunc)


#===============================================================
def class_header(class_dtbl, nscname, scope):
    cname = scope.name
    class_dtbl.append(f"""// {cname} class""")
    class_dtbl.append(f"""    {{MP_OBJ_NEW_QSTR(MP_QSTR_{cname}), (mp_obj_t)&{nscname}_type }},""")

    proto = [f"""typedef struct _{nscname}_obj_t {{"""]
    proto.append('    mp_obj_base_t base;')

    cvar = []
    cdef = []
    initializer = []


    for name, v_type_def in scope.v:
        decl, init_line = cvar_any(name, v_type_def)
        proto.append( decl )
        initializer.append(init_line)

    proto.append(f"""}} {nscname}_obj_t;""")
    scope.initializer = '\n'.join(initializer)
    return proto

ptypes = {}


#===============================================================
def build_class_body(namespace, nscname, scope):
    proto = []
    proto.append(f"""
""")

# TODO: decl of __init__
# STATIC mp_obj_t object___init__(mp_obj_t self) {
#    (void)self;
#    return mp_const_none;
# }
# STATIC MP_DEFINE_CONST_FUN_OBJ_1(object___init___obj, object___init__);

    # forward decl of type + ctor

    # m_new_obj_with_finaliser could be used too

    proto.append(f"""
const mp_obj_type_t {nscname}_type;  //forward decl

mp_obj_t
{nscname}_make_new( const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args ) {{

    mp_arg_check_num(n_args, n_kw, {0}, {0}, true);

    {nscname}_obj_t *self = m_new_obj({nscname}_obj_t);

    self->base.type = &{nscname}_type;

// self->hash = object_id++;
// printf("Object serial #%d\\n", self->hash );

{scope.initializer}

    return MP_OBJ_FROM_PTR(self);
}}
""")

    # default __repr__ and locals() table
    proto.append(f"""
void
{nscname}_print( const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind ) {{
    // get a ptr to the C-struct of the object
    {nscname}_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // print the number
    mp_printf (print, "<{namespace}.{scope.name} at 0x%p>", self);
}}
""")

    return proto







#===============================================================
def build_dict_table(namespace,mtype, *tables):
    table = []
    for frag in tables:
        table.extend(frag)
        table.append('')
    table = '\n'.join( table )
    return f'''

STATIC const mp_{mtype}_elem_t {namespace}_dict_table[] = {{
{table}
//  {{NULL, NULL, 0, NULL}} // cpython
}};

STATIC MP_DEFINE_CONST_DICT({namespace}_dict, {namespace}_dict_table);

'''


#===============================================================
def build_methods_block(namespace, block_dict, func_table, scope):

    if scope.level>0:
        has_self = 1
        nscname = f'{namespace}_{scope.name}'
    else:
        has_self = 0
        nscname = namespace

    for ndef, child_scope in scope.children.items():


        block_dict.append(f"    {{MP_OBJ_NEW_QSTR(MP_QSTR_{ndef}), (mp_obj_t)&{nscname}_{ndef}_obj }},")

        argc, c_type, p_type, c_code = build_method(nscname, has_self, child_scope)

        func_table.append(f'''

STATIC mp_obj_t // {c_type} -> {p_type}
{nscname}_{ndef}(size_t argc, const mp_obj_t *argv) {{
{c_code}
}}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({nscname}_{ndef}_obj, 0, {argc}, {nscname}_{ndef});
''')



def build_module_class(namespace, module_dtbl, class_dtbl, func_table, scope):
    cname = scope.name

    # top level module
    if not scope.level:
        has_self = 0
        deftable = module_dtbl
        build_methods_block(namespace, module_dtbl, func_table,scope)
        return


    func_table.append(f'''
//    Begin :  class {cname}:
''')

    # classes
    has_self = 1
    deftable = class_dtbl
    nscname = f'{namespace}_{cname}'


    class_local_dict = []

    for l in class_header(class_dtbl, nscname, scope):
        yield l

    for l in build_class_body(namespace, nscname, scope):
        yield l

    class_dtbl.append('')


    build_methods_block(namespace, class_local_dict, func_table, scope)

    local_dict = build_dict_table(nscname, 'map', class_local_dict )

    # struct + local dict of the above class. registered later in global dict

    func_table.append(f'''

// ++++++++ class {cname} interface +++++++

{local_dict}

const mp_obj_type_t {nscname}_type = {{

    // "inherit" the type "{scope.ancestor}"
    {{ &mp_type_{scope.ancestor} }},

     // give it a name
    .name = MP_QSTR_{scope.name},

     // give it a print-function
    .print = {nscname}_print,

     // give it a constructor
    .make_new = {nscname}_make_new,

     // and its locals members
    .locals_dict = (mp_obj_dict_t*)&{nscname}_dict,
}};

// End:  **************** class {cname} ************
''')








def cify(namespace, tlv):
    tlv_table = []
    module_dtbl = ['// __main__']
    class_dtbl = ['// Classes : ','']
    func_table = []

    ext_hook = ['// builtins']
    ext_hook.append(f'  {{MP_OBJ_NEW_QSTR(MP_QSTR___name__), MP_OBJ_NEW_QSTR(MP_QSTR_{namespace}) }},')
    ext_hook.append(f'  {{MP_OBJ_NEW_QSTR(MP_QSTR___file__), MP_OBJ_NEW_QSTR(MP_QSTR_flashrom) }},')
    ext_hook.append('')
    ext_hook.append('// extensions')

    if namespace == 'embed':
        ext_hook.append('    {MP_OBJ_NEW_QSTR(MP_QSTR_on_del), MP_ROM_PTR(&mp_type_on_del) },')

    ext_hook.append('')

    while len(tlv):
        cmstruct = tlv.pop()
        for l in build_module_class(namespace, module_dtbl, class_dtbl, func_table, cmstruct):
            yield l


    for l in func_table:
        yield l
    func_table.clear()


    # map or rom_map ?
    global_dict = build_dict_table(namespace, 'map', ext_hook, class_dtbl, module_dtbl )


    tlv_table.append(f"""

// global module dict :

{global_dict}

//const mp_obj_module_t STATIC
PyModuleDef module_{namespace} = {{
    .base = {{ &mp_type_module }},
    .globals = (mp_obj_dict_t*)&{namespace}_dict,
}};

// Register the module to make it available
MP_REGISTER_MODULE(MP_QSTR_{namespace}, module_{namespace}, MODULE_{namespace.upper()}_ENABLED);
""" )
    yield '\n'.join(tlv_table)





























#
