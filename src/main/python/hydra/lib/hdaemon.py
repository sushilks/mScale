__author__ = 'AbdullahS'

from pprint import pprint, pformat   # NOQA
import zmq
import time
import logging
from hydra.lib import util
from hydra.lib.utility.h_threading import HThreading

l = util.createlogger('HDaemon', logging.INFO)
# l.setLevel(logging.DEBUG)


class HDaemonBase(object):
    def __init__(self, **kwargs):
        self.port = kwargs.pop("port")
        self.data = {}  # Dict calling class can use to store data, can be fetched later
        l.info("HdaemonBase initiated...")
        self.t_exceptions = []
        self.h_threading = HThreading()

    def set_data(self, data={}):
        self.data = data  # probably deepcopy will be better, will see

    def thread_cb(self, t_exceptions):
        for exception in t_exceptions:
            self.t_exceptions.append(exception)
            l.info(exception)

class HDaemonRepSrv(HDaemonBase):
    def __init__(self, **kwargs):
        l.info("HdaemonRepSrv initiated...")
        super(HDaemonRepSrv, self).__init__(**kwargs)

    def run(self):
        l.info("HdaemonRepSrv spawning run thread...")
        self.h_threading.start_thread(self.thread_cb, self.start)

    def start(self):
        l.info("Binding zmq REP socket...")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:%s" % self.port)
        l.info("Done Binding zmq REP socket...")
        while True:
            #  Wait for next request from client
            message = self.socket.recv()
            l.info("Received request: [%s]", message)
            # Stop and return
            if message == "stop":
                self.stop()
                return
            elif message == "stats_req":
                time.sleep (1)
                self.socket.send("World from %s" % self.port)

    def stop(self):
        l.info("Received stop signal, closing socket")
        self.socket.close()
