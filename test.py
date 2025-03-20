import time
from genasync import *

def tick_tock(delay):
    def fn(delay):
        print('tick')
        time.sleep(delay/2)
        print('tock')
        time.sleep(delay/2)
    return BackgroundTask(lambda: fn(delay))

print('start')
task = tick_tock(2)
task.wait()
print('done')
