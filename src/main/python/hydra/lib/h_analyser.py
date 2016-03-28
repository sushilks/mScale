__author__ = 'AbdullahS, sushil'

from pprint import pprint, pformat   # NOQA
import zmq
import logging
import sys
from hydra.lib import util, hdaemon_pb2

l = util.createlogger('HDaemon', logging.INFO)
# l.setLevel(logging.DEBUG)

zmq_context = zmq.Context()
zmq_poller = zmq.Poller()


class HAnalyser(object):
    def __init__(self, server_ip, server_port, task_id=''):
        l.debug("Hydra Analyser initiated...")
        self.server_ip = server_ip
        self.port = server_port
        self.task_id = task_id
        self.data = {}  # This is where all received data will be stored
        self.context = zmq_context
        self.poller = zmq_poller
        self.req_msg = hdaemon_pb2.CommandMessage()
        self.resp_msg = hdaemon_pb2.ResponseMessage()
        l.debug("Connecting to server at [%s:%s]", self.server_ip, self.port)
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://%s:%s" % (self.server_ip, self.port))
        l.debug("Conneced...")

    def do_req_resp(self, cmd, timeout=10000, **kwargs):
        req_msg = self.req_msg
        req_msg.Clear()
        req_msg.type = hdaemon_pb2.CommandMessage.SUBCMD
        # req_msg.cmd = hdaemon_pb2.CommandMessage.Command()
        req_msg.cmd.cmd_name = cmd
        for key in kwargs:
            arg = req_msg.cmd.argument.add()
            arg.name = key
            t = type(kwargs[key])
            if t is int:
                arg.intValue = kwargs[key]
            elif t is float:
                arg.floatValue = kwargs[key]
            else:
                arg.strValue = str(kwargs[key])

        l.debug("Sending message %s" % req_msg)
        self.socket.send(req_msg.SerializeToString())
        l.debug("Waiting for server to respond...")
        self.poller.register(self.socket, zmq.POLLIN)
        msgs = dict(self.poller.poll(timeout))
        self.poller.unregister(self.socket)
        if self.socket in msgs and msgs[self.socket] == zmq.POLLIN:
            rep = self.socket.recv()
        else:
            # Timed out
            l.error("Timed out waiting for server at %s:%s" % (self.server_ip, self.port))
            return (False, {})
        self.resp_msg.ParseFromString(rep)
        l.debug("Got response %s" % self.resp_msg)
        status = self.resp_msg.status
        rdic = {}
        for itm in self.resp_msg.resp:
            if itm.HasField("strValue"):
                rdic[itm.name] = itm.strValue
            elif itm.HasField("intValue"):
                rdic[itm.name] = itm.intValue
            elif itm.HasField("floatValue"):
                rdic[itm.name] = itm.floatValue
            else:
                rdic[itm.name] = True

        if status == 'exception':
            l.error("Remote exception at :" + self.task_id)
            l.error(rdic['__r'])
        l.debug("Received STATUS=" + pformat(status))
        l.debug("    -> ::" + pformat(rdic))
        if len(rdic) == 1 and '__r' in rdic:
            return (status, rdic['__r'])
        return (status, rdic)

    def do_ping(self):
        # TODO: (ABdullahS) See if it makes sense to reset the client here
        (status, response) = self.do_req_resp('ping')
        return (status == 'ok') and (response == 'pong')

    def stop(self):
        self.socket.close()


if __name__ == '__main__':
    # Standalone implementation goes here if required
    sys.exit(0)
