__author__ = 'AbdullahS'

from pprint import pprint, pformat   # NOQA
import zmq
import time
import logging
from hydra.lib import util

l = util.createlogger('HDaemon', logging.INFO)
# l.setLevel(logging.DEBUG)


class HAnalyserBase(object):
    def __init__(self, **kwargs):
        self.server_ip = kwargs.pop("server_ip")
        self.port = kwargs.pop("server_port")

        self.context = zmq.Context()
        print "Connecting to server..."
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect ("tcp://localhost:%s" % self.port)
        l.info("Binding zmq REQ socket...")

class HAnalyser(HAnalyserBase):
    def __init__(self, **kwargs):
        l.info("Hydra Analyser initiated...")
        super(HAnalyser, self).__init__(**kwargs)

    def do_req(self):
        print "Sending request "
        self.socket.send ("Hello")
        #  Get the reply.
        message = self.socket.recv()
        print "Received reply ", "[", message, "]"

if __name__ == '__main__':
    kwargs = {}
    kwargs.update({"server_ip": "10.10.0.2"})
    kwargs.update({"server_port": 14400})
    ha = HAnalyser(**kwargs)
    raw_input("do_req")
    ha.do_req()
