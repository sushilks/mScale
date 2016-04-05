__author__ = 'AbdullahS'

import logging
import os
import time
import psutil
import pika
from hydra.lib import util
from hydra.lib.hdaemon import HDaemonRepSrv
from hydra.lib.childmgr import ChildManager
from pprint import pformat

l = util.createlogger('HSub', logging.INFO)


class HDRmqsRepSrv(HDaemonRepSrv):
    def __init__(self, port):
        self.msg_cnt = 0  # message count, other option is global, making progress
        HDaemonRepSrv.__init__(self, port)
        self.register_fn('getstats', self.get_stats)
        self.register_fn('resetstats', self.reset_stats)

    def get_stats(self):
        process = psutil.Process()
        self.run_data['stats']['net']['end'] = psutil.net_io_counters()
        self.run_data['stats']['cpu']['end'] = process.cpu_times()
        self.run_data['stats']['mem']['end'] = process.memory_info()
        duration = self.run_data['last_msg_time'] - self.run_data['first_msg_time']
        if duration == 0:
            self.run_data['rate'] = 0
        else:
            self.run_data['rate'] = self.run_data['msg_cnt'] / duration

        return ('ok', self.run_data)

    def reset_stats(self):
        l.info("RESETTING SUB STATS")
        process = psutil.Process()
        self.run_data = {'msg_cnt': 0, 'first_msg_time': 0, 'last_msg_time': 0, 'stats': {}}
        self.run_data['stats']['net'] = {'start': psutil.net_io_counters()}
        self.run_data['stats']['cpu'] = {'start': process.cpu_times()}
        self.run_data['stats']['mem'] = {'start': process.memory_info()}
        self.msg_cnt = 0
        return ('ok', 'stats reset')

    def callback(self, ch, method, properties, body):
        self.msg_cnt = self.msg_cnt + 1
        if self.run_data['first_msg_time'] == 0:
            self.run_data['first_msg_time'] = time.time()
        index, messagedata = body.split()
        # l.info("%s, %s", index, messagedata)
        # Update data for THIS client, later to be queried
        self.run_data['msg_cnt'] = self.msg_cnt
        self.run_data['last_msg_time'] = time.time()


def run10(argv):
    pwd = os.getcwd()
    l.info("CWD = " + pformat(pwd))
    cmgr = ChildManager()
    myenv = os.environ.copy()
    cmd = './hydra hydra.rmqtest.rmq_sub.run'.split(' ') + argv[1:]
    # TODO: (AbdullahS) Find a better way to do this
    if "mock" in myenv:
        cmd = 'hydra hydra.rmqtest.rmq_sub.run'.split(' ') + argv[1:]
    cwd = None
    for idx in range(0, 10):
        myenv = os.environ.copy()
        myenv["PORT0"] = myenv["PORT" + str(idx)]
        l.info("Launch%d:" % idx + " cwd=" + " CMD=" + pformat(cmd) + " PORT0=" + str(myenv["PORT0"]))
        cmgr.add_child('p' + str(idx), cmd, cwd, myenv)
    cmgr.launch_children()
    cmgr.wait()


def run(argv):
    pub_ip = ""
    l.info("JOB RUN : " + pformat(argv))
    if len(argv) > 1:
        pub_ip = argv[1]
    if not pub_ip:
        raise Exception("Rmq-sub needs a pub server to subscribe to, pub_ip"
                        " can not be empty pub_ip[%s]" % (pub_ip))

    # Initalize HDaemonRepSrv
    sub_rep_port = os.environ.get('PORT0')
    hd = HDRmqsRepSrv(sub_rep_port)
    hd.reset_stats()
    hd.run()

    l.info("RabbitMQ SUB client connecting to RabbitMQ PUB server at [%s]" % (pub_ip))
    credentials = pika.PlainCredentials('hydra', 'hydra')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=pub_ip, credentials=credentials))
    channel = connection.channel()
    channel.exchange_declare(exchange='pub', type='fanout')
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='pub', queue=queue_name)
    l.info("RabbitMQ SUB client succesfully connected to RabbitMQ PUB server at [%s]" % (pub_ip))

    hd.msg_cnt = 0
    channel.basic_consume(hd.callback, queue=queue_name, no_ack=True)
    channel.start_consuming()
