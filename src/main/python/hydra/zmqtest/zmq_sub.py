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
        self.recv_rate = 0
        self.reconnect_cnt = 0
        self.reconnect_rate = 0
        HDaemonRepSrv.__init__(self, port)
        self.register_fn('getstats', self.get_stats)
        self.register_fn('resetstats', self.reset_stats)
        self.register_fn('updateconfig', self.update_config)
        self.reset_stats()

    def get_stats(self):
        process = psutil.Process()
        self.run_data['stats']['msg_cnt'] = self.msg_cnt
        self.run_data['stats']['net:end'] = json.dumps(psutil.net_io_counters())
        self.run_data['stats']['cpu:end'] = json.dumps(process.cpu_times())
        self.run_data['stats']['mem:end'] = json.dumps(process.memory_info())
        self.run_data['stats']['reconnect_cnt'] = self.reconnect_cnt
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
        self.reconnect_cnt = 0
        return ('ok', 'stats reset')

    def update_config(self, recv_rate, reconnect_rate):
        self.recv_rate = float(recv_rate)
        self.reconnect_rate = reconnect_rate
        l.info("Updating SUB Metrics recv_rate = " + pformat(self.recv_rate) +
               " reconnect_rate = " + pformat(self.reconnect_rate))
        return ('ok', None)


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
    hd.msg_cnt = 0
    start_idx = 0

    while True:
        socket = context.socket(zmq.SUB)
        topicfilter = ""

        l.info("SUB client connecting to PUB server at [%s:%s]" % (pub_ip, pub_port))
        socket.connect("tcp://%s:%s" % (pub_ip, pub_port))
        l.info("SUB client successfully connected to PUB server at [%s:%s]" % (pub_ip, pub_port))
        socket.setsockopt(zmq.SUBSCRIBE, topicfilter)

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
            hd.run_data['last_msg_time_r'] = time.time()
            hd.run_data['stats']['last_msg_time'] = json.dumps(hd.run_data['last_msg_time_r'])
            # rate limit the receive
            if hd.recv_rate != 0:
                # Check the rate from beginning of first message to now
                duration = float(hd.msg_cnt) / hd.recv_rate
                current_duration = time.time() - hd.run_data['first_msg_time_r']
                if current_duration < duration:
                    sleep_time = duration - current_duration
                    if sleep_time > 1:
                        sleep_time = 1
                    time.sleep(sleep_time)
            # re-connect
            if hd.reconnect_rate != 0:
                current_duration = time.time() - hd.run_data['first_msg_time_r']
                num_reconnects = int(hd.reconnect_rate * current_duration)
                if (num_reconnects > hd.reconnect_cnt):
                    l.info("expected Reconnect = " + pformat(num_reconnects) + " reconnect_cnt = " +
                    pformat(hd.reconnect_cnt))
                    break
        hd.reconnect_cnt += 1
        l.info('Closing Socket. Will try to reconnect. Current msg cnt=' + pformat(hd.msg_cnt))
        socket.close()
