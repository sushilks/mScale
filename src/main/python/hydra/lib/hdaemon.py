__author__ = 'AbdullahS, sushil'

from pprint import pprint, pformat   # NOQA
import zmq
import logging
import json
from hydra.lib import util
from hydra.lib.utility.h_threading import HThreading

l = util.createlogger('HDaemon', logging.INFO)
# l.setLevel(logging.DEBUG)


class HDaemonRepSrv(object):
    def __init__(self, port):
        l.info("initiated..., REP port[%s]", port)
        self.port = port
        self.data = {}  # Dict calling class can use to store data, can be fetched later
        self.t_exceptions = []
        self.h_threading = HThreading()
        self.cbfn = {}

    def thread_cb(self, t_exceptions):
        for exception in t_exceptions:
            self.t_exceptions.append(exception)
            l.error(exception)

    def run(self):
        l.info("spawning run thread...")
        self.register_fn('ping', self.ping_task)
        self.h_threading.start_thread(self.thread_cb, self.start)

    def register_fn(self, token, fn):
        l.debug("Registering function for [%s]" % token)
        if token in self.cbfn:
            raise Exception('token [%s] is already registered' % token)
        self.cbfn[token] = fn

    def ping_task(self, arg):
        return ('ok', 'pong')

    def send_response(self, status, msg):
        self.socket.send(json.dumps([status, msg]))

    def start(self):
        l.info("Binding zmq REP socket...")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:%s" % self.port)
        l.info("Done Binding zmq REP socket...")
        while True:
            #  Wait for next request from client
            raw_message = self.socket.recv()
            message = json.loads(raw_message)
            l.info("Received request: [%s]", raw_message)
            # Stop and return
            if message[0] == "stop":
                l.info("Stopping.")
                self.stop()
                return
            elif not message[0] in self.cbfn:
                msg = "UNKNOWN message [%s] received... " % message[0]
                status_code = 'error'
                l.error(msg)
                self.send_response(status_code, msg)
            else:
                fn = self.cbfn[message[0]]
                if len(message) == 1 or not message[1]:
                    sts, msg = fn(None)
                else:
                    sts, msg = fn(message[1])
                l.info("Sending Response STATUS=" + pformat(sts) + " MSG=" + pformat(msg))
                self.send_response(sts, msg)

    def stop(self):
        l.info("Received stop signal, closing socket")
        self.socket.close()
