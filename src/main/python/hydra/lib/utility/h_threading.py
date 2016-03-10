import threading
import traceback


class HThread(object):

    """
    HThreading Wrapper.
    """

    def __init__(self):
        self.thread_exceptions = []
        self.thread = None  # This will be used to hold threading.Thread object

    def _get_my_tid(self):
        return self.thread.ident
        raise AssertionError("could not determine the thread's id")

    def _start_thread(self, callback_fn, fn, daemon=False, **kwargs):
        thread_kwargs = kwargs.pop('kwargs', {})
        thread_args = kwargs.pop('args', ())
        self.thread = threading.Thread(target=self._wrapper, args=(fn, thread_args, thread_kwargs, callback_fn))
        if daemon:
            self.thread.setDaemon(True)
        self.thread.start()

    def _is_alive(self):
        return self.thread.is_alive()

    def _wrapper(self, fn, args, kwargs, callback_fn):
        try:
            fn(*args, **kwargs)
        except:
            self.thread_exceptions.append(traceback.format_exc())
            callback_fn(self.thread_exceptions)


class HThreading(object):

    """
    HThreading class accessible to user. Takes care of wrapping around
    HThread
    """

    def __init__(self):
        self.running_threads = []
        self.thread_id_fn = {}

    def start_thread(self, callback_fn, fn, daemon=False, **kwargs):
        t = HThread()
        t._start_thread(callback_fn, fn, daemon, **kwargs)
        self.running_threads.append(t)
        self.thread_id_fn.update({t.thread: fn})
        return t

    def join_all(self, timeout=None):
        t_list = []
        for t in self.running_threads:
            t.thread.join(timeout)
            # Remove the dead thread from running threads
            if not t._is_alive():
                t_list.append(t)

        for t in t_list:
            self.running_threads.remove(t)
