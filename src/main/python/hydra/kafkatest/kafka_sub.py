__author__ = 'annyz'

import logging
import os
import sys
import time
import psutil
import json
from hydra.lib import util
from hydra.lib.hdaemon import HDaemonRepSrv
from hydra.lib.childmgr import ChildManager
from pprint import pformat
from kafka import KafkaConsumer

l = util.createlogger('HSub', logging.INFO)


class HDKafkasRepSrv(HDaemonRepSrv):
    def __init__(self, port):
        self.msg_cnt = 0  # message count, other option is global, making progress
        self.recv_rate = 0
        HDaemonRepSrv.__init__(self, port)
        self.register_fn('getstats', self.get_stats)
        self.register_fn('resetstats', self.reset_stats)

    def get_stats(self):
        process = psutil.Process()
        self.run_data['stats']['msg_cnt'] = self.msg_cnt
        self.run_data['stats']['net:end'] = json.dumps(psutil.net_io_counters())
        self.run_data['stats']['cpu:end'] = json.dumps(process.cpu_times())
        self.run_data['stats']['mem:end'] = json.dumps(process.memory_info())
        self.run_data['stats']['rate'] = self.run_data['stats']['msg_cnt'] / (
            self.run_data['last_msg_time_r'] - self.run_data['first_msg_time_r'])

        return ('ok', self.run_data['stats'])

    def reset_stats(self):
        l.info("RESETTING SUB STATS")
        process = psutil.Process()
        self.run_data = {'msg_cnt': 0, 'first_msg_time': 0, 'last_msg_time': 0, 'stats': {}}
        self.run_data['stats']['net'] = {'start': psutil.net_io_counters()}
        self.run_data['stats']['cpu'] = {'start': process.cpu_times()}
        self.run_data['stats']['mem'] = {'start': process.memory_info()}
        self.run_data['first_msg_time_r'] = 0
        self.run_data['last_msg_time_r'] = 1
        self.msg_cnt = 0
        return ('ok', 'stats reset')


def run10(argv):
    pwd = os.getcwd()
    l.info("CWD = " + pformat(pwd))
    cmgr = ChildManager()
    myenv = os.environ.copy()
    cmd = './hydra hydra.kafkatest.kafka_sub.run'.split(' ') + argv[1:]
    if "mock" in myenv:
        cmd = 'hydra hydra.kafkatest.kafka_sub.run'.split(' ') + argv[1:]
    cwd = None
    for idx in range(0, 10):
        myenv = os.environ.copy()
        myenv["PORT0"] = myenv["PORT" + str(idx)]
        l.info("Launch%d:" % idx + " cwd=" + " CMD=" + pformat(cmd) + " PORT0=" + str(myenv["PORT0"]))
        cmgr.add_child('p' + str(idx), cmd, cwd, myenv)
    cmgr.launch_children()
    cmgr.wait()
    from subprocess import call
    call(["kafka/bin/kafka-topics.sh", "--zookeeper", "127.0.0.1:2181", "--delete", "--topic", "base-topic"])
    sys.exit(0)


def run(argv):
    old_client = True

    l.info("JOB RUN : " + pformat(argv))
    pub_ip = ''
    if len(argv) > 3:
        topic_name = argv[1]
        pub_ip = argv[2]
        consumer_max_buffer_size = argv[3]
        l.info("Kafka SUB will subscribe to topic [%s]" % topic_name)
        l.info("Kafka Broker is hosted in [%s]" % pub_ip)
        l.info("Kafka Consumer MAX Buffer size is [%s]" % consumer_max_buffer_size)
        consumer_max_buffer_size = int(consumer_max_buffer_size)

    if not topic_name:
        raise Exception("Kafka-Sub needs a TOPIC to subscribe to.")
    if not pub_ip:
        raise Exception("Kafka Broker IP is not provided to consumer.")

    # Initalize HDaemonRepSrv
    sub_rep_port = os.environ.get('PORT0')
    hd = HDKafkasRepSrv(sub_rep_port)
    hd.reset_stats()
    hd.run()
    hd.msg_cnt = 0

    # Init Kafka Consumer
    l.info("Kafka SUB client (consumer) connecting to Kafka Server (broker) at localhost:9092")
    kafka_server = str(pub_ip) + ":9092"
    if old_client:
        consumer = KafkaConsumer(bootstrap_servers=[kafka_server],
                             auto_offset_reset='earliest')
        consumer.max_buffer_size = consumer_max_buffer_size
        # Specify the list of topics which the consumer will subscribe to
        consumer.subscribe([topic_name])
    # else:
        # client = KafkaClient(hosts=kafka_server)
        # topic = client.topics['test']
        # consumer = topic.get_simple_consumer()

    while True:
        for message in consumer:
            # If first message:
            if hd.msg_cnt == 0:
                hd.run_data['first_msg_time_r'] = time.time()
                hd.run_data['stats']['first_msg_time'] = json.dumps(hd.run_data['first_msg_time_r'])
                l.info("[Kafka-Sub] Setting the 'first_msg_time' to = " +
                       pformat(hd.run_data['stats']['first_msg_time']))
            # Increment received message counter
            hd.msg_cnt = hd.msg_cnt + 1

            hd.run_data['last_msg_time_r'] = time.time()
            hd.run_data['stats']['last_msg_time'] = json.dumps(hd.run_data['last_msg_time_r'])

            # Limit the 'receive' rate if necessary
            if hd.recv_rate != 0:
                # Check the rate from beginning of first message to now
                duration = float(hd.msg_cnt) / hd.recv_rate
                current_duration = time.time() - hd.run_data['first_msg_time_r']
                if current_duration < duration:
                    sleep_time = duration - current_duration
                    if sleep_time > 1:
                        sleep_time = 1
                    time.sleep(sleep_time)
            # duration = hd.run_data['last_msg_time_r'] - hd.run_data['first_msg_time_r']
            hd.run_data['msg_cnt'] = hd.msg_cnt
