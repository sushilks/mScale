import os
import sys
import threading
import time
import traceback
import logging
import ctypes
import inspect
import uuid

class HThread(object):

    """
    HThreading Wrapper.
    """

    def __init__(self):
        self.thread_exceptions = []
        self.thread = None  # This will be used to hold threading.Thread object

    def _get_my_tid(self):
        """
        determines this (self's) thread id
        i-e self.ident
        """
        return self.thread.ident
        raise AssertionError("could not determine the thread's id")

    def _start_thread(self, callback_fn, fn, daemon=False, **kwargs):
        """
        Starts a thread :)
        args:
        callback_fn : Callback function to be invoked in case the thread raises
                      User MUST provide a call back function to catch exceptions
                      This will prevent thread exceptions to be lost !
        fn :          Function to execute in the thread
        kwargs :      Args to thread function
        daemon:       Flag to start thread in daemon mode. Default is false.
        """
        thread_kwargs = kwargs.pop('kwargs', {})
        thread_args = kwargs.pop('args', ())
        wait_event = kwargs.pop('event', ())
        self.thread = threading.Thread(target=self._wrapper, args=(fn, thread_args, thread_kwargs, callback_fn))
        if daemon:
            self.thread.setDaemon(True)
        self.thread.start()

    def _is_alive(self):
        """
        Check if current thread is alive
        """
        return self.thread.is_alive()

    def _wrapper(self, fn, args, kwargs, callback_fn):
        """
        Function to be used internally by the class to wrap a user function
        """
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
        """
        Starts a thread :)
        args:
        callback_fn : Callback function to be invoked in case the thread raises
                      User MUST provide a call back function to catch exceptions
                      This will prevent thread exceptions to be lost !
        fn :          Function to execute in the thread
        kwargs :      Args to thread function
        daemon:       Option to run thread in daemon mode. Default is false.
        """
        t = HThread()
        t._start_thread(callback_fn, fn, daemon, **kwargs)
        self.running_threads.append(t)
        self.thread_id_fn.update({t.thread: fn})
        return t

    def join_all(self, timeout=None):
        """
        Wait for all threads to return
        """
        t_list = []
        for t in self.running_threads:
            t.thread.join(timeout)
            # Remove the dead thread from running threads
            if not t._is_alive():
                t_list.append(t)

        for t in t_list:
            self.running_threads.remove(t)

    def all_alive(self):
        """
        Check if all threads are alive
        """
        t_list = []
        for t in self.running_threads:
            if t._is_alive():
                t_list.append(t)
        if len(t_list) == len(self.running_threads):
            return True
        else:
            return False

    def any_alive(self):
        """
        Check if any thread is alive
        """
        for t in self.running_threads:
            if t._is_alive():
                return True
        return False
