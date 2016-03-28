__author__ = 'sushil, abdullahS'

import zmq
import logging
import os
import time
import psutil
import json
from hydra.lib import util
from hydra.lib.hdaemon import HDaemonRepSrv
from hydra.lib.childmgr import ChildManager
from pprint import pformat

l = util.createlogger('HSub', logging.INFO)


class HDZmqsRepSrv(HDaemonRepSrv):
    def __init__(self, port):
        self.msg_cnt = 0  # message count, other option is global, making progress
        HDaemonRepSrv.__init__(self, port)
        self.register_fn('stats', self.get_stats)
        self.register_fn('reset', self.reset_stats)
        self.reset_stats()

    def get_stats(self):
        process = psutil.Process()
        self.run_data['stats']['msg_cnt'] = self.msg_cnt
        self.run_data['stats']['net:end'] = json.dumps(psutil.net_io_counters())
        self.run_data['stats']['cpu:end'] = json.dumps(process.cpu_times())
        self.run_data['stats']['mem:end'] = json.dumps(process.memory_info())
        self.run_data['stats']['rate'] = self.run_data['stats']['msg_cnt'] / (
            self.run_data['last_msg_time_r'] - self.run_data['first_msg_time_r'])
        return ('ok', self.run_data['stats'])

    def reset_stats(self):
        l.info("RESETTING SUB STATS")
        process = psutil.Process()
        self.run_data = {'stats': {}}
        self.run_data['stats'] = {'msg_cnt': 0, 'first_msg_time': 0, 'last_msg_time': 0}
        self.run_data['stats']['net:start'] = json.dumps(psutil.net_io_counters())
        self.run_data['stats']['cpu:start'] = json.dumps(process.cpu_times())
        self.run_data['stats']['mem:start'] = json.dumps(process.memory_info())
        self.run_data['first_msg_time_r'] = 0
        self.run_data['last_msg_time_r'] = 1
        self.msg_cnt = 0
        return ('ok', 'stats reset')


def run10_inst(cmd):
    pwd = os.getcwd()
    l.info("CWD = " + pformat(pwd))
    cmgr = ChildManager()
    cwd = None
    for idx in range(0, 10):
        myenv = os.environ.copy()
        myenv["PORT0"] = myenv["PORT" + str(idx)]
        l.info("Launch%d:" % idx + " cwd=" + " CMD=" + pformat(cmd) + " PORT0=" + str(myenv["PORT0"]))
        cmgr.add_child('p' + str(idx), cmd, cwd, myenv)
    cmgr.launch_children()
    cmgr.wait()


def run10cpp(argv):
    cmd = './zmq_sub'.split(' ') + argv[1:]
    run10_inst(cmd)


def run10(argv):
    cmd = './hydra hydra.zmqtest.zmq_sub.run'.split(' ') + argv[1:]
    run10_inst(cmd)


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
    hd = HDZmqsRepSrv(sub_rep_port)
    hd.reset_stats()
    hd.run()

    # Socket to SUB to PUB server
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    topicfilter = ""

    l.info("SUB client connecting to PUB server at [%s:%s]" % (pub_ip, pub_port))
    socket.connect("tcp://%s:%s" % (pub_ip, pub_port))
    l.info("SUB client successfully connected to PUB server at [%s:%s]" % (pub_ip, pub_port))
    socket.setsockopt(zmq.SUBSCRIBE, topicfilter)

    hd.msg_cnt = 0
    start_idx = 0
    while True:
        string = socket.recv()
        if hd.msg_cnt == 0:
            hd.run_data['first_msg_time_r'] = time.time()
            hd.run_data['stats']['first_msg_time'] = json.dumps(hd.run_data['first_msg_time_r'])
            l.info("Setting the first_msg_time to = " + pformat(hd.run_data['stats']['first_msg_time']))
        hd.msg_cnt = hd.msg_cnt + 1
        index, messagedata = string.split()
        iidx = int(index)
        if (start_idx != iidx):
            l.info("Missing FROM IDX = %d :: GOT MESSAGE %s %d", start_idx, index, iidx)
            start_idx = iidx
        start_idx += 1
        # Update data for THIS client, later to be queried
        # TODO: Add checks on index and message data.
        hd.run_data['last_msg_time_r'] = time.time()
        hd.run_data['stats']['last_msg_time'] = json.dumps(hd.run_data['last_msg_time_r'])
