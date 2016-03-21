__author__ = 'sushil, abdullahS'

import zmq
import logging
import os
import time
import psutil
from hydra.lib import util
from hydra.lib.hdaemon import HDaemonRepSrv
from hydra.lib.childmgr import ChildManager
from pprint import pformat

l = util.createlogger('HSub', logging.INFO)


class HDZmqsRepSrv(HDaemonRepSrv):
    def __init__(self, port, run_data):
        self.run_data = run_data
        self.msg_cnt = 0  # message count, other option is global, making progress
        HDaemonRepSrv.__init__(self, port)
        self.register_fn('stats', self.get_stats)
        self.register_fn('reset', self.reset_stats)

    def get_stats(self, args):
        process = psutil.Process()
        self.run_data['stats']['net']['end'] = psutil.net_io_counters()
        self.run_data['stats']['cpu']['end'] = process.cpu_times()
        self.run_data['stats']['mem']['end'] = process.memory_info()
        self.run_data['rate'] = self.run_data['msg_cnt'] / (
            self.run_data['last_msg_time'] - self.run_data['first_msg_time'])
        return ('ok', self.run_data)

    def reset_stats(self, args):
        l.info("RESETTING SUB STATS")
        process = psutil.Process()
        self.run_data = {'msg_cnt': 0, 'first_msg_time': 0, 'last_msg_time': 0, 'stats': {}}
        self.run_data['stats']['net'] = {'start': psutil.net_io_counters()}
        self.run_data['stats']['cpu'] = {'start': process.cpu_times()}
        self.run_data['stats']['mem'] = {'start': process.memory_info()}
        self.msg_cnt = 0
        return ('ok', 'stats reset')


def run10(argv):
    pwd = os.getcwd()
    l.info("CWD = " + pformat(pwd))
    cmgr = ChildManager()
    cmd = './hydra hydra.zmqtest.zmq_sub.run'.split(' ') + argv[1:]
    cwd = None
    for idx in range(0, 10):
        myenv = os.environ.copy()
        myenv["PORT0"] = myenv["PORT" + str(idx)]
        l.info("Launch%d:" % idx + " cwd=" + " CMD=" + pformat(cmd) + " PORT0=" + str(myenv["PORT0"]))
        cmgr.add_child('p' + str(idx), cmd, cwd, myenv)
    cmgr.launch_children()
    cmgr.wait()


def run(argv):
    pub_port = ""
    pub_ip = ""
    l.info("JOB RUN : " + pformat(argv))
    if len(argv) > 2:
        pub_ip = argv[1]
        pub_port = argv[2]
        int(pub_port)
    if (not pub_ip or (not pub_port)):
        raise Exception("zmq-sub needs a pub server to subscribe to, pub_ip/pub_port"
                        " can not be empty pub_ip[%s], pub_port[%s]" % (pub_ip, pub_port))

    # Initalize HDaemonRepSrv
    sub_rep_port = os.environ.get('PORT0')
    run_data = {}
    hd = HDZmqsRepSrv(sub_rep_port, run_data)
    hd.reset_stats(None)
    hd.run()

    # Socket to SUB to PUB server
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    topicfilter = ""

    l.info("SUB client connecting to PUB server at [%s:%s]" % (pub_ip, pub_port))
    socket.connect("tcp://%s:%s" % (pub_ip, pub_port))
    l.info("SUB client succesfully connected to PUB server at [%s:%s]" % (pub_ip, pub_port))
    socket.setsockopt(zmq.SUBSCRIBE, topicfilter)

    hd.msg_cnt = 0
    while True:
        string = socket.recv()
        hd.msg_cnt = hd.msg_cnt + 1
        if hd.run_data['first_msg_time'] == 0:
            hd.run_data['first_msg_time'] = time.time()
        index, messagedata = string.split()
        # l.info("%s, %s", index, messagedata)
        # Update data for THIS client, later to be queried
        # TODO: Add checks on index and message data.
        hd.run_data['msg_cnt'] = hd.msg_cnt
        hd.run_data['last_msg_time'] = time.time()
