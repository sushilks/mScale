__author__ = 'sushil, abdullahS'

import zmq
import random
import time
from hydra.lib.hdaemon import HDaemonRepSrv


def run(argv):
    #kwargs = {}
    #kwargs.update({"port": 14400})
    #hd = HDaemonRepSrv(**kwargs)
    #hd.run()
    #msg_count = 1000  # Total messages to send
    #raw_input()

    pub_port = "15556"
    msg_delay = 0.01
    if len(argv) > 1:
        msg_delay = argv[1]
        float(msg_delay)

    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:%s" % pub_port)

    print "PUB server initiating sending all DATA"
    msg_count = 1000  # Number of messages to send
    for index in range(msg_count):
        messagedata = "msg%d" % index
        print "%d %s" % (index, messagedata)
        socket.send("%d %s" % (index, messagedata))
        time.sleep(msg_delay)

    print "PUB server finished sending all DATA"
