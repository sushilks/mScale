__author__ = 'sushil, abdullahS'

import zmq
import time
import logging
import os
from hydra.lib import util
l = util.createlogger('HPub', logging.INFO)


def send_pub_data(socket, total_msgs=10000, msg_delay=0.01, msg_batch=100):
    l.info("PUB server initiating sending [%s] messages, in batches [%s] with delay[%f]",
           total_msgs, msg_batch, float(msg_delay))
    cnt = 0
    for index in range(int(total_msgs)):
        messagedata = "msg%d" % index
        # l.info("%d %s" % (index, messagedata))
        socket.send("%d %s" % (index, messagedata))
        if cnt >= int(msg_batch):
            time.sleep(float(msg_delay))
            cnt = 0
        cnt += 1
    socket.close()


def run(argv):
    pub_port = "15556"  # probably do it randomly as well ?
    if len(argv) > 3:
        total_msgs = argv[1]
        msg_batch = argv[2]
        msg_delay = argv[3]
        int(total_msgs)
        int(msg_batch)
        float(msg_delay)

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
            send_pub_data(pub_socket, total_msgs=total_msgs, msg_delay=msg_delay, msg_batch=msg_batch)
            l.info("PUB server finished sending all DATA, closing pub_socket")
            pub_rep_socket.send("DONE")
            pub_rep_socket.close()
            return
        else:
            l.info("UNKNOWN MESSAGE RECEIVED")
            continue
