__author__ = 'sushil, abdullahS'

import zmq
import logging
import os
from hydra.lib import util
from hydra.lib.hdaemon import HDaemonRepSrv
l = util.createlogger('HSub', logging.INFO)


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
    hd = HDaemonRepSrv(sub_rep_port)
    hd.run()

    # Socket to SUB to PUB server
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    topicfilter = ""

    l.info("SUB client connecting to PUB server at [%s:%s]" % (pub_ip, pub_port))
    socket.connect("tcp://%s:%s" % (pub_ip, pub_port))
    l.info("SUB client succesfully connected to PUB server at [%s:%s]" % (pub_ip, pub_port))
    socket.setsockopt(zmq.SUBSCRIBE, topicfilter)

    # Ideally socket will have a method to return client id, skimming through
    # /usr/lib/python2.7/dist-packages/zmq/sugar/socket.py didnt yield a quick soln.. hacking...
    client_id = str(socket)
    client_id = client_id[client_id.rfind("0x") + 2:len(client_id) - 1]
    client_data = {}
    client_data[client_id] = {}
    l.info("Client id [%s] " % client_id)

    l.info("Client iniating recv")
    index_list = []
    while True:
        string = socket.recv()
        index, messagedata = string.split()
        # l.info("%s, %s", index, messagedata)
        index_list.append(index)
        # Update data for THIS client, later to be queried
        client_data[client_id].update({"msg_count": len(index_list)})
        hd.data.update(client_data)
