import threading as _t

class _Tasks:
    _tls = _t.local()

    @classmethod
    def get(cls):
        if not hasattr(cls._tls, 'tasks'):
            cls._tls.tasks = _Tasks()
        return cls._tls.tasks

    def __init__(self):
        self.tasks = []
        self.idx = 0

    def add(self, task):
        self.tasks.append(task)

    def _yield_step(self): #??
        ran = 0
        disabled = 0
        for task in list(self.tasks):
            if task._active.value:
                continue
            if not task._enabled:
                disabled += 1
                continue
            with task._active:
                dly = task._step()
                ran += 1
            if task.is_done:
                self.tasks.remove(task)
            elif dly is not None:
                with self._cv:
                    def on_notify(dly, task):
                        if dly.is_ready:
                            with self._cv:
                                task._enabled = True
                                self._cv.notify()
                    dly.set_notify(task, on_notify)
                    task._enabled = False
            yield
        if ran == 0 and disabled > 0:
            with self._cv:
                has_en = False
                while has_en:
                    for task in self.tasks:
                        if not task._active.value and task._enabled:
                            has_en = True
                    if not has_en:
                        self._cv.wait()



    def step(self):
        assert len(self.tasks) > 0

        if self.idx >= len(self.tasks):
            self.idx = 0

        # TODO: task._enabled logic, and self._cv.wait() on no enabled tasks

        active = 0
        while self.tasks[self.idx]._active.value and len(self.tasks) > active:
            active += 1
            self.idx += 1
            if self.idx >= len(self.tasks):
                self.idx = 0

        assert active < len(self.tasks)

        task = self.tasks[self.idx]
        self.idx += 1

        with task._active:
            dly = task._step()
        if dly is not None:
            def on_notify(dly, task):
                if dly.is_ready:
                    with self._cv:
                        task._enabled = True
                        self._cv.notify()
            dly.set_notify(task, on_notify)
            with self._cv:
                task._enabled = False

        if task.is_done:
            idx = self.tasks.index(task)
            assert idx >= 0 and idx < len(self.tasks)
            self.tasks.remove(task)
            if self.idx >= idx:
                self.idx -= 1

class _ActiveCtx:
    def __init__(self):
        self.value = False

    def __enter__(self):
        self.value = True
        return self

    def __exit__(self, *parg):
        self.value = False

class Task:
    def __init__(self, generator):
        if isinstance(generator, Task):
            raise TypeError('Cannot clone tasks')
        self._gen = generator
        self._tasks = _Tasks.get()
        self._cv = _t.Condition()
        self._done = False
        self._res = None
        self._err = None
        self._active = _ActiveCtx()
        self._tasks.add(self)
        # Always run the first step immediatly
        self._step()

    def _step(self):
        if _Tasks.get() != self._tasks:
            raise RuntimeError('cannot step task from another thread')
        try:
            return next(self._gen)
        except StopIteration as stop:
            if stop.value is not None:
                self._res = stop.value
            self._done = True
        except Exception as err:
            self._err = err
            self._done = True

    @property
    def is_done(self):
        return self._done

    @property
    def result(self):
        return self.wait()

    def wait(self):
        if _Tasks.get() != self._tasks:
            with self._cv:
                while not self.is_done:
                    self._cv.wait()
        else:
            while not self.is_done:
                self._tasks.step()

        if self._err is not None:
            raise self._err
        return self._res

class BackgroundTask:
    def __init__(self, fn):
        self._fn = fn
        self._cv = _t.Condition()
        self._res = None
        self._err = None
        self._done = False
        def run():
            try:
                res = fn()
                with self._cv:
                    self._res = res
                    self._done = True
                    self._cv.notify_all()
            except Exception as err:
                with self._cv:
                    self._err = err
                    self._done = True
                    self._cv.notify_all()
            self._result = fn()
        self._thread = _t.Thread(target=run, daemon=True)
        self._thread.start()

    @property
    def is_done(self):
        with self._cv:
            return self._done
        
    @property
    def result(self):
        return self.wait()
    
    def wait(self):
        with self._cv:
            while not self._done:
                self._cv.wait()

        if self._err:
            raise self._err
        return self._res
