from robot.running.context import EXECUTION_CONTEXTS

class AsyncLibrary:
    def __init__(self):
        self._thread_pool = {}
        self._last_thread_handle = 0

    def async_run(self, keyword, *args, **kwargs):
        ''' Executes the provided Robot Framework keyword in a separate thread and immediately returns a handle to be used with async_get '''
        handle = self._last_thread_handle
        thread = self._threaded(keyword, *args, **kwargs)
        thread.start()
        self._thread_pool[handle] = thread
        self._last_thread_handle += 1
        return handle

    def async_get(self, handle):
        ''' Blocks until the thread created by async_run returns '''
        assert handle in self._thread_pool, 'Invalid async call handle'
        t = self._thread_pool[handle]
        if t.isAlive():
            result = t.result_queue.get()
        else:
            result = None if t.result_queue.empty() else t.result_queue.get_nowait()
        del self._thread_pool[handle]
        return result

    def _get_handler_from_keyword(self, keyword):
        ''' Gets the Robot Framework handler associated with the given keyword '''
        if EXECUTION_CONTEXTS.current is None:
            raise RobotNotRunningError('Cannot access execution context')
        return EXECUTION_CONTEXTS.current.get_handler(keyword)

    def _threaded(self, keyword, *args, **kwargs):
        import Queue
        import threading
        
        def wrapped_f(q, *args, **kwargs):
            ''' Calls the decorated function and puts the result in a queue '''
            f = self._get_handler_from_keyword(keyword)
            kwargsTuple = tuple('%s=%s' % (key, kwargs[key]) for key in kwargs.keys())
            ret = f.run(EXECUTION_CONTEXTS.current, args + kwargsTuple)
            q.put(ret)

        q = Queue.Queue()
        t = threading.Thread(target=wrapped_f, args=(q,)+args, kwargs=kwargs)
        t.result_queue = q
        return t
