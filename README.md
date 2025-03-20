# genasync
Generator based python async library

*** Note: this is currently filled with my hopes and dreams, not what's actually here yet

I find python's built-in async functions overly complicated and cumbersome to use. This isn't meant to be efficient or better, just easier to use and extend for anyone whose brain works like mine.

All async logic (after the first yield) runs in Task.wait() or Task.result. Tasks can call each other's wait functions as normal (of course doing something like task_a.wait() inside task_b and task_b.wait() inside task_a will hang forever).

Creating an async function is just a wrapped generator function:
```python
import time
from genasync import Task

def naive_async_delay(t):
    def fn(t):
        start = time.time()
        while time.time() - start < t:
            yield
        return 'hello world'
    return Task(fn(t))

print(time.time())
print(naive_async_delay(1).wait())
print(time.time())

```

Empty async functions (useful for placholders, or multiple implementations) just need to add a dummy yield:
```python
import time
from genasync import Task

def dummy_async():
    def fn():
        print('evaluated right away')
        return 'hello world 2'
        yield
    return Task(fn())

print(time.time())
v = dummy_async()
print(v.wait())
print(time.time())

```

And things that don't really follow the async way can be run as a background task (separate thread)
```python
import time
from genasync import Task

def bkg_fn(delay):
    def fn(delay):
        time.sleep(delay / 2)
        print('half time')
        time.sleep(delay / 2)
        print('full time')
        return 'hello background world'
    return BackgroundTask(lambda: fn(delay))

print('start')
bkg = bkg_fn(5)
time.sleep(10)
print('waiting')
print(bkg.wait())
print('done')

```

yield can pass a condition to wait on instead of maddly polling everything
```python
import time
from genasync import Task, Delay, EPoll

def better_async_delay(t):
    def fn(t):
        start = time.time()
        while time.time() - start < t:
            yield Delay(0.1) # don't wake us up for at least 0.1 seconds
        return 'hello world'
    return Task(fn(t))

# random linux only example that will probably not exist in this library
def async_read(file, len):
    def fn(file, len):
        with EPoll(file, EPoll.RD) as epoll:
            while not epoll.is_ready:
                yield epoll
                # epolls can be combined internally, so only one extra thread is
                # needed for all epolls. Yes the wakeup logic it threaded, but
                # all async fn logic is run in the main thread like everything else
            return file.read(len)
    return Task(fn(file, len))

print(time.time())
print(better_async_delay(1).wait())
print(time.time())

```

Custom Delay events can be created, they need an event.set_notify(fn) method, and an event.is_ready property. the set_notify(fn) registers a fn to be called (with the event as the argument) when the ready status changes. This is expected to be called from another monitoring thread. is_ready must be thread-safe and is not alowed to change from True to False until the next set_notify(fn) is called... Maybe just support delays and move that onto the main thread if everything's been asked to wait... I'm not sure having separate threads for events gives any benifits over just using BackgroundTasks... This fancy library might end up just being used for background tasks in the end... Though something like real async io would fit a single separate thread fairly well...

TODO: Debugging exceptions thrown inside a task can be very confusing... need to figure out a good way to clearly separate the unrelated waiting events in the stack from the actually exception paths...
