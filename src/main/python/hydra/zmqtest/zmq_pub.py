__author__ = 'sushil, abdullahS'

import zmq
import random
import time
import logging
import os
from hydra.lib import util
from hydra.lib.hdaemon import HDaemonRepSrv
from hydra.zmqtest import zmq_config
l = util.createlogger('HPub', logging.INFO)



def send_pub_data(socket, msg_count=10000, msg_delay=0.01):
    l.info("PUB server initiating sending [%d] messages, with delay[%f]", msg_count, float(msg_delay))
    for index in range(msg_count):
        messagedata = "msg%d" % index
        #print "%d %s" % (index, messagedata)
        #l.info("%d %s" % (index, messagedata))
        socket.send("%d %s" % (index, messagedata))
        time.sleep(float(msg_delay))
    socket.close()

def run(argv):
    msg_count = int(zmq_config.msg_count)
    msg_delay = float(zmq_config.msg_delay)
    l.info(msg_count)
    l.info(msg_delay)
    pub_port = "15556"

    #msg_delay = 0.01
    #if len(argv) > 2:
    #    msg_delay = argv[1]
    #    msg_count= argv[2]
    #    float(msg_delay)
    #    #int(msg_count)

    # init and bind pub server
    pub_context = zmq.Context()
    pub_socket = pub_context.socket(zmq.PUB)
    pub_socket.bind("tcp://*:%s" % pub_port)

    # init simple zmq rep server, this is used to listen
    # for the signal to start sending data
    pub_rep_port = os.environ.get('PORT0')
    l.info("Starting zmq REP server at port [%s]", pub_rep_port)
    pub_rep_context = zmq.Context()
    pub_rep_socket = pub_rep_context.socket(zmq.REP)
    pub_rep_socket.bind("tcp://*:%s" % pub_rep_port)
    l.info("Done Binding zmq REP socket...")

    # start receive
    while True:
        #  Wait for signal from the client
        message = pub_rep_socket.recv()
        l.info("Received request: [%s]", message)
        # Stop and return
        if message == "start":
            send_pub_data(pub_socket, msg_count=msg_count, msg_delay=msg_delay)
            l.info("PUB server finished sending all DATA, closing pub_socket")
            pub_rep_socket.send("DONE")
            pub_rep_socket.close()
            return
        else:
            l.info("UNKNOWN MESSAGE RECEIVED")
            continue
