import sys
import os
import glob



def print_exception(e, out, **kw):
    kw['file'] = out
    __import__('traceback').print_exc(**kw)


sys.print_exception = print_exception

from . import *


USER_C_MODULES = os.environ.get('USER_C_MODULES','cmod')


for pym in glob.glob( os.path.join(USER_C_MODULES,'*.pym')):

    namespace = os.path.basename(pym)[:-4]

    with open(pym,'r') as source:

        # will will convert code to scopes tree, and will yield anything before first class/def
        # using single line C comment style (//) for python comments style (#)

        headlines = ["""/* http://github.com/pmp-p  target pym:%s */""" % pym ]
        for line in py2x( namespace,  sys.argv[0], source):

            headlines.append( line )

        print("Header : %s lines" % len(headlines) )

        if 0:
            print(f"Begin:====================== py2py [{pym}] ========================")

            for pyline in to_py():
                pass
                #print(pyline)

            code = '\n'.join(pylines)
            try:
                bytecode = compile( code, '<modgen>', 'exec')
            except Exception as e:
                print("================ %s ================" % pym)
                print(code)
                print("================================")
                sys.print_exception(e, sys.stderr)
                raise SystemExit(1)

        # create build folder, will host makefile and transpiled code
        mod_dir = f"{USER_C_MODULES}/{namespace}"
        os.makedirs(mod_dir, exist_ok=True)

        # create the makefile

        with open(f"{mod_dir}/micropython.mk","w") as makefile:
            makefile.write(f"""
{namespace.upper()}_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(wildcard $({namespace.upper()}_MOD_DIR)/*.c)

# add module folder to include paths if needed
CFLAGS_USERMOD += -I$({namespace.upper()}_MOD_DIR)
""")

        # transpile to C

        ctarget = f"{mod_dir}/mod{namespace}.c"
        print()
        print(f"Begin:====================== py2c [{pym}] ========================")
        with open(ctarget,'w') as code:
            for line in to_c(headlines):
                print(line, file=code)

        print(f"End:====================== transpiled [{ctarget}] ========================")


sys.exit(0)
