__author__ = 'sushil'

import zmq
import random
import time
import threading
import sys
import os
# REQ -> REP
# PUB -> SUB


class Test(object):
    def __init__(self, argv):
        p0 = os.environ.get('PORT0')
        print("REQ PORT0 = " + p0)
        self.port_rep = p0
        self.port_pub = argv[1]
        self.ip_port_sub = argv[2]
        self.shutdown = False
        self.pub_enabled = True
        self.send_delay = 1
        self.thread_rep = self.startthread(target=self.rep_task, args=("rep", self.port_rep))
        self.thread_pub = self.startthread(target=self.pub_task, args=("pub", self.port_pub))
        self.thread_sub = self.startthread(target=self.sub_task, args=("sub", self.ip_port_sub))
        try:
            while 1:
                sys.stdout.flush()
                time.sleep(1)
        except KeyboardInterrupt:
            print("Exiting")
            self.shutdown = True
        sys.exit(0)
        self.thread_rep.join()
        self.thread_pub.join()
        self.thread_sub.join()
        return 0

    def startthread(self, target, args):
        t = threading.Thread(target=target, args=args)
        t.daemon = True
        t.start()
        return t

    def rep_task(self, name, port_rep):
        if (port_rep == "0"):
            return
        ctx = zmq.Context()
        # create req-rep socket
        socket_rep = ctx.socket(zmq.REP)
        socket_rep.bind("tcp://*:%s" % port_rep)
        while not self.shutdown:
            message = socket_rep.recv()
            print("REP: GOT Message %s" % message)
            if message == 'ping':
                socket_rep.send('pong')
            elif message == 'disable_pub':
                socket_rep.send('ok')
                self.pub_enabled = False
            elif message == 'enable_pub':
                socket_rep.send('ok')
                self.pub_enabled = True
            elif message == 'reset_pub':
                socket_rep.send('ok')
                self.pub_msg_cnt = 0
            elif message == 'reset_sub':
                socket_rep.send('ok')
                self.sub_msg_cnt = 0
            elif message == 'cnt_pub':
                socket_rep.send(str(self.pub_msg_cnt))
            elif message == 'cnt_sub':
                socket_rep.send(str(self.sub_msg_cnt))
            elif message.find('delay') == 0:
                d = message.split(':')[1]
                self.send_delay = float(d)
                socket_rep.send('ok')
            else:
                socket_rep.send('Unknown message %s' % message)

    def pub_task(self, name, port_pub):
        if (port_pub == "0"):
            return
        ctx = zmq.Context()
        # publish socket
        socket_pub = ctx.socket(zmq.PUB)
        socket_pub.bind("tcp://*:%s" % port_pub)
        self.pub_msg_cnt = 0
        while not self.shutdown:
            if self.pub_enabled:
                topic = random.randrange(9999, 10005)
                messagedata = self.pub_msg_cnt
                self.pub_msg_cnt += 1
                print "PUB [%d] %d %d" % (self.pub_msg_cnt, topic, messagedata)
                socket_pub.send("%d %d" % (topic, messagedata))
            time.sleep(self.send_delay)

    def sub_task(self, name, ip_port_sub):
        if (ip_port_sub == "0"):
            return
        ctx = zmq.Context()
        # subscribe socket
        socket_sub = ctx.socket(zmq.SUB)
        socket_sub.connect("tcp://%s" % ip_port_sub)
        socket_sub.setsockopt(zmq.SUBSCRIBE, '')
        total_value = 0
        self.sub_msg_cnt = 0
        while not self.shutdown:
            string = socket_sub.recv()
            topic, messageData = string.split()
            total_value += int(messageData)
            self.sub_msg_cnt += 1
            print "SUB:: [%d] %s %s" % (self.sub_msg_cnt, topic, messageData)


if '__main__' == __name__:
    argv = sys.argv
    if (len(argv) != 4):
        print("Usages %s <port_rep> <port_pub> <ip_port_sub>")
        print("Use 0 if you dont want to create a service i.e. set <port_pub> to 0 if pub is not needed")
        exit(1)
    print ("Running command : " + argv[0] + ' ' + '.'.join(argv[1:]))
    exit(Test(argv))
