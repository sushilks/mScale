__author__ = 'AbdullahS'

from pprint import pprint, pformat   # NOQA
import zmq
import time
import logging
import json
from hydra.lib import util

l = util.createlogger('HDaemon', logging.INFO)
# l.setLevel(logging.DEBUG)


class HAnalyserBase(object):
    def __init__(self, **kwargs):
        self.server_ip = kwargs.pop("server_ip")
        self.port = kwargs.pop("server_port")
        self.data = {}  # This is where all received data will be stored

        self.context = zmq.Context()
        l.info("Connecting to server at [%s:%s]", self.server_ip, self.port)
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://%s:%s" % (self.server_ip, self.port))
        l.info("Conneced...")

class HAnalyser(HAnalyserBase):
    def __init__(self, **kwargs):
        l.info("Hydra Analyser initiated...")
        super(HAnalyser, self).__init__(**kwargs)

    def do_req(self, msg):
        #print "Sending request "
        # TODO: (AbdullahS): Make sure pub actually started sending data
        self.socket.send(msg)
        l.info("Waiting for PUB server to finish sending all data..")
        rep = self.socket.recv()
        if rep == "DONE":
            l.info("Pub server finished sending all DATA..")
            self.socket.close()

    def do_req_update_data(self, msg):
        l.info("Sending request [%s] to sub_client at [%s:%s]", msg, self.server_ip, self.port)
        self.socket.send(msg)
        #  Get the reply.
        #l.info("waiting for resp")
        rep = self.socket.recv()
        #l.info(rep)
        self.data.update(json.loads(rep))
        self.socket.close()

    def get_data(self):
        return self.data


if __name__ == '__main__':
    # Standalone implementation goes here if required
    sys.exit(0)
