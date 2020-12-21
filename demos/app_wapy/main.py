#!wapy -i -u -B

print(sys.version)

print('Hello from wapy.html')


if sys.argv:
    print('script :', sys.argv.pop() )
else:
    print('wasi arguments stack N/I')
print('args :', sys.argv )



#test()
