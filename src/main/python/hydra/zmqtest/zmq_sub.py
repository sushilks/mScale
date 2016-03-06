__author__ = 'sushil, abdullahS'

import zmq
import random
import time
from hydra.lib.hdaemon import HDaemonRepSrv


def run(argv):
    pub_port = "15556"
    pub_ip = "localhost"
    if len(argv) > 2:
        pub_ip = argv[1]
        pub_port = argv[2]
        int(pub_port)

    ## Initalize HDaemonRepSrv
    kwargs = {}
    kwargs.update({"port": 14400})
    hd = HDaemonRepSrv(**kwargs)
    hd.run()
    raw_input("================================")



    ## Socket to talk to server
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    topicfilter = ""

    print "SUB client connecting to PUB server at [%s:%s]" % (pub_ip, pub_port)
    socket.connect ("tcp://%s:%s" % (pub_ip, pub_port))
    print "SUB client succesfully connected to PUB server at [%s:%s]" % (pub_ip, pub_port)
    socket.setsockopt(zmq.SUBSCRIBE, topicfilter)
    # Ideally socket will have a method to return client id, skimming through
    # /usr/lib/python2.7/dist-packages/zmq/sugar/socket.py didnt yield a quick soln.. hacking...
    client_id = str(socket)
    client_id = client_id[client_id.rfind("0x") + 2:len(client_id) - 1]
    print "Client id [%s] " % client_id

    # init perf logger
    #sys_cmd = PySysCommand("mkdir -p /tmp/zmq_client_logs")
    #sys_cmd.run()
    #perf_log_file = "/tmp/zmq_client_logs/%s.log" % client_id
    #log = init_logger(perf_log_file)
    runtime = 0
    print "Client iniating recv"
    while True:
        string = socket.recv()
        index, messagedata = string.split()
        print index, messagedata
        #log.info("client_id=%s,latency=%s,total_runtime=%f,index=%s,messagedata=%s", client_id, latency, runtime, index, messagedata)
