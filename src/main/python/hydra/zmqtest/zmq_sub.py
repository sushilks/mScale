__author__ = 'sushil, abdullahS'

import zmq
import logging
import os
import time
from hydra.lib import util
from hydra.lib.hdaemon import HDaemonRepSrv
l = util.createlogger('HSub', logging.INFO)


class HDZmqsRepSrv(HDaemonRepSrv):
    def __init__(self, port, run_data):
        self.run_data = run_data
        HDaemonRepSrv.__init__(self, port)
        self.register_fn('stats', self.get_stats)

    def get_stats(self, args):
        self.run_data['rate'] = self.run_data['msg_cnt'] / (
            self.run_data['last_msg_time'] - self.run_data['first_msg_time'])
        return ('ok', self.run_data)

    def reset_stats(self, args):
        self.run_data = {'msg_cnt': 0, 'first_msg_time': 0, 'last_msg_time': 0}


def run(argv):
    pub_port = ""
    pub_ip = ""
    if len(argv) > 2:
        pub_ip = argv[1]
        pub_port = argv[2]
        int(pub_port)
    if (not pub_ip or (not pub_port)):
        raise Exception("zmq-sub needs a pub server to subscribe to, pub_ip/pub_port"
                        " can not be empty pub_ip[%s], pub_port[%s]" % (pub_ip, pub_port))

    # Initalize HDaemonRepSrv
    sub_rep_port = os.environ.get('PORT0')
    run_data = {'msg_cnt': 0, 'first_msg_time': 0, 'last_msg_time': 0}
    hd = HDZmqsRepSrv(sub_rep_port, run_data)
    hd.run()

    # Socket to SUB to PUB server
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    topicfilter = ""

    l.info("SUB client connecting to PUB server at [%s:%s]" % (pub_ip, pub_port))
    socket.connect("tcp://%s:%s" % (pub_ip, pub_port))
    l.info("SUB client succesfully connected to PUB server at [%s:%s]" % (pub_ip, pub_port))
    socket.setsockopt(zmq.SUBSCRIBE, topicfilter)

    # SK:Not sure what the purpose of adding client id is, The receiver can easily categorise based on who they
    # received the data from, Disabling it for now, will add again if needed.
    # Ideally socket will have a method to return client id, skimming through
    # /usr/lib/python2.7/dist-packages/zmq/sugar/socket.py didnt yield a quick soln.. hacking...
    # client_id = str(socket)
    # client_id = client_id[client_id.rfind("0x") + 2:len(client_id) - 1]
    # run_data[client_id] = {'msg_cnt':0, 'first_msg_time':0 , 'last_msg_time': 0}
    # l.info("Client id [%s] initiating receive" % client_id)
    cnt = 0
    while True:
        string = socket.recv()
        cnt = cnt + 1
        if run_data['first_msg_time'] == 0:
            run_data['first_msg_time'] = time.time()
        index, messagedata = string.split()
        # l.info("%s, %s", index, messagedata)
        # Update data for THIS client, later to be queried
        # TODO: Add checks on index and message data.
        run_data['msg_cnt'] = cnt
        run_data['last_msg_time'] = time.time()
