__author__ = 'sushil'

import zmq
import random
import time


def zmq_pub(argv):
    port = " 15556"
    if len(argv) > 1:
        port = argv[1]
        int(port)

    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:%s" % port)

    msg_cnt = 0
    while True:
        topic = random.randrange(9999, 10005)
        messagedata = random.randrange(1, 215) - 80
        msg_cnt += 1
        print "[%d] %d %d" % (msg_cnt, topic, messagedata)
        socket.send("%d %d" % (topic, messagedata))
        time.sleep(1)


def zmq_sub(argv):
    pub_port = "15556"
    pub_ip = "localhost"
    if len(argv) > 2:
        pub_ip = argv[1]
        pub_port = argv[2]
        int(pub_port)

    context = zmq.Context()
    socket = context.socket(zmq.SUB)

    print "Collecting updates from weather server...."
    socket.connect("tcp://" + pub_ip + ":%s" % pub_port)

    # topicfilter = "10001"
    # socket.setsockopt(zmq.SUBSCRIBE, topicfilter)
    socket.setsockopt(zmq.SUBSCRIBE, '')

    total_value = 0
    msg_cnt = 0
    while True:
        string = socket.recv()
        topic, messageData = string.split()
        total_value += int(messageData)
        msg_cnt += 1
        print "[%d] %s %s" % (msg_cnt, topic, messageData)
