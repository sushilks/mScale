__author__ = 'AbdullahS, sushil'

from pprint import pprint, pformat   # NOQA
import zmq
import time
import logging
import sys
import json
from hydra.lib import util, hdaemon_pb2

l = util.createlogger('HDaemon', logging.INFO)
# l.setLevel(logging.DEBUG)


tout_60s = 60000
tout_30s = 30000
tout_10s = 10000


class HAnalyser(object):
    def __init__(self, server_ip, server_port, task_id='', debug=False):
        if debug:
            l.setLevel(logging.DEBUG)
        l.debug("Hydra Analyser initiated...")
        self.server_ip = server_ip
        self.port = server_port
        self.task_id = task_id
        self.data = {}  # This is where all received data will be stored
        self.context = zmq.Context.instance()
        self.poller = zmq.Poller()
        self.req_msg = hdaemon_pb2.CommandMessage()
        self.resp_msg = hdaemon_pb2.ResponseMessage()
        l.debug("Connecting to server at [%s:%s]", self.server_ip, self.port)
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://%s:%s" % (self.server_ip, self.port))
        l.debug("Connected...")

    def do_req_resp(self, cmd, timeout=10000, **kwargs):
        self.do_req_only(cmd, **kwargs)
        return self.do_resp_only(timeout)

    def do_req_only(self, cmd, **kwargs):
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
            elif util.istext(str(kwargs[key])):
                arg.strValue = str(kwargs[key])
            else:
                arg.byteValue = str(kwargs[key])

        l.debug("Sending message %s" % req_msg)
        self.socket.send(req_msg.SerializeToString())

    def do_resp_only(self, timeout=10000):
        l.debug("Waiting for server to respond...")
        self.poller.register(self.socket, zmq.POLLIN)
        msgs = dict(self.poller.poll(timeout))
        self.poller.unregister(self.socket)
        if self.socket in msgs and msgs[self.socket] == zmq.POLLIN:
            rep = self.socket.recv()
        else:
            # Timed out
            l.error("Timed out waiting for server at %s:%s task_id[%s]" % (self.server_ip, self.port, self.task_id))
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
            elif itm.HasField("byteValue"):
                rdic[itm.name] = itm.byteValue
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

    def start_test(self, **kwargs):
        l.info("Sending Start test to %s", self.task_id)
        (status, resp) = self.do_req_resp(cmd='teststart', timeout=tout_60s, **kwargs)
        l.info("Start test came back with status " + pformat(status) + " resp = " + pformat(resp))
        assert(status == 'ok')

    def stop_test(self):
        l.info("Sending Stop test to %s", self.task_id)
        (status, resp) = self.do_req_resp(cmd='teststop', timeout=tout_60s)
        l.info("Stop test came back with status " + pformat(status) + " resp = " + pformat(resp))
        assert(status == 'ok')

    def wait_for_testend(self):
        while True:
            (status, resp) = self.do_req_resp(cmd='teststatus', timeout=tout_60s)
            if status != 'ok':
                l.error("Status = " + pformat(status))
                l.error("resp = " + pformat(resp))
                raise Exception("Error while waiting for test Status.")
            l.debug("Wait for testend :: Status = " + pformat(status) +
                    "resp = " + pformat(resp))
            if resp == 'done' or resp == 'stopping' or resp == 'stopped':
                break
            time.sleep(5)

    def get_stats(self):
        (status, resp) = self.do_req_resp(cmd='getstats')
        if status != 'ok':
            l.error("Failed to get stats from task_id=" + self.task_id +
                    "  Status = " + pformat(status) + " resp = " + pformat(resp))
        assert(status == 'ok')
        for itm in resp.keys():
            if (type(resp[itm]) is str or type(resp[itm]) is unicode):  # NOQA
                try:
                    resp[itm] = json.loads(resp[itm])
                except:
                    pass
        return resp

    def reset_stats(self):
        (status, resp) = self.do_req_resp(cmd='resetstats')
        assert(status == 'ok')
        return resp

    def update_config(self, **kwargs):
        l.debug("Updating the test metric on %s: " % self.task_id + pformat(kwargs))
        (status, resp) = self.do_req_resp(cmd='updateconfig', **kwargs)
        assert(status == 'ok')
        return resp

    def stop(self):
        self.socket.close()


if __name__ == '__main__':
    # Standalone implementation goes here if required
    sys.exit(0)
