# wapy.es6 helper
delay = 3

# hide vm flow
embed.os_hideloop()

# show only synchronous python flow
embed.show_trace()

def interlude(info):
    ln = embed.show_trace() # must be first line
    aio.vm.script.trace(ln)
    aio.vm.script.finalize
    print("\n"*4,info,' in %s seconds : ' % delay, end='')
    aio_suspend()

    for x in range(delay):
        time.sleep(1)
        print(delay-x, end="")
    else:
      print(" go!")
    # flush pending stdio
    aio.flush()


