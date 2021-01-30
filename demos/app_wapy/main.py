#!wapy -i -u -B

print(sys.version)

print('Hello from wapy.html')


if sys.argv:
    print('script :', sys.argv.pop() )
else:
    print('wasi arguments stack N/I (yet)')
print('args :', sys.argv )

async def main(argc, argv, env):

    print('Hi')
    while 1:
        window.document.title = 'tic/---'
        await aio.sleep(0.5)
        window.document.title = '---/tac'
        await aio.sleep(0.5)


aio.run(main(0, [], {}))
#test()
