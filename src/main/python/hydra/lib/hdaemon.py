__author__ = 'AbdullahS, sushil'

from pprint import pprint, pformat   # NOQA
import zmq
import logging
import json
import traceback
from hydra.lib import util
from hydra.lib.utility.h_threading import HThreading
from hydra.lib import hdaemon_pb2

l = util.createlogger('HDaemon', logging.INFO)
# l.setLevel(logging.DEBUG)


class HDaemonRepSrv(object):
    def __init__(self, port):
        l.info("initiated... REP port[%s]", port)
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
        self.register_fn('teststart', self.test_start)
        self.register_fn('teststop', self.test_stop)
        self.register_fn('getstats', self.get_stats)
        self.register_fn('resetstats', self.reset_stats)
        self.register_fn('teststatus', self.test_status)
        self.register_fn('updateconfig', self.update_config)
        self.h_threading.start_thread(self.thread_cb, self.start)

    def register_fn(self, token, fn):
        l.debug("Registering function for [%s]" % token)
        if token in self.cbfn:
            l.info('token [%s] is already registered' % token)
        self.cbfn[token] = fn

    def ping_task(self):
        return ('ok', 'pong')

    def test_start(self, **kwargs):
        l.info('TEST START NEED TO BE IMPLEMENTED')
        return('ok', None)

    def test_stop(self):
        l.info('TEST STOP NEED TO BE IMPLEMENTED')
        return('ok', None)

    def test_status(self):
        l.info('TEST STATUS NEED TO BE IMPLEMENTED')
        return('ok', None)

    def get_stats(self):
        l.info('GET STATS NEED TO BE IMPLEMENTED')
        return('ok', None)

    def reset_stats(self):
        l.info('RESET STATS NEED TO BE IMPLEMENTED')
        return('ok', None)

    def update_config(self, **kwargs):
        l.info('UPDATE CONFIG NEED TO BE IMPLEMENTED')
        return('ok', None)

    def send_response(self, status, msg):
        self.socket.send(json.dumps([status, msg]))

    def start(self):
        l.info("Binding zmq REP socket...")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:%s" % self.port)
        l.info("Done Binding zmq REP socket...")
        msg = hdaemon_pb2.CommandMessage()
        rmsg = hdaemon_pb2.ResponseMessage()
        while True:
            #  Wait for next request from client
            raw_message = self.socket.recv()
            msg.ParseFromString(raw_message)
            # message = json.loads(raw_message)
            l.info("Received request: [%s]", str(msg.type))
            # Stop and return
            if msg.type == hdaemon_pb2.CommandMessage.STOP:
                l.info("Stopping.")
                self.stop()
                return
            elif ((msg.type == hdaemon_pb2.CommandMessage.SUBCMD) and
                  (not msg.HasField("cmd") or msg.cmd.cmd_name not in self.cbfn)):
                if msg.HasField("cmd"):
                    msg = "UNKNOWN message [%s] received... " % msg.cmd.cmd_name
                else:
                    msg = "UNKNOWN message with not cmd field received... "
                status_code = 'error'
                l.error(msg)
                self.send_response(status_code, msg)
            else:
                fn = self.cbfn[msg.cmd.cmd_name]

                kwargs = {}
                for targ in msg.cmd.argument:
                    if targ.HasField("intValue"):
                        kwargs[targ.name] = targ.intValue
                    elif targ.HasField("floatValue"):
                        kwargs[targ.name] = targ.floatValue
                    elif targ.HasField("strValue"):
                        kwargs[targ.name] = targ.strValue
                    else:
                        kwargs[targ.name] = True
                try:
                    sts, msghash_t = fn(**kwargs)
                except:
                    sts = 'exception'
                    msghash_t = traceback.format_exc()
                rmsg.Clear()
                rmsg.status = sts
                if type(msghash_t) is dict:
                    msghash = msghash_t
                else:
                    msghash = {}
                    msghash['__r'] = msghash_t

                if msghash:
                    for key in msghash:
                        r = rmsg.resp.add()
                        r.name = str(key)
                        if type(msghash[key]) is int:
                            r.intValue = msghash[key]
                        elif type(msghash[key]) is float:
                            r.floatValue = msghash[key]
                        else:
                            r.strValue = str(msghash[key])

                l.info("Sending Response STATUS=" + pformat(sts) + " MSG=" + pformat(msghash))
                # self.send_response(sts, msg)
                self.socket.send(rmsg.SerializeToString())

    def stop(self):
        l.info("Received stop signal, closing socket")
        self.socket.close()
