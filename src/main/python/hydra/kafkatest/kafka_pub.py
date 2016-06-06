__author__ = 'annyz'

import time
import logging
import os
import psutil
import json
from pprint import pprint, pformat   # NOQA
from hydra.lib import util
from hydra.lib.hdaemon import HDaemonRepSrv
from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError

l = util.createlogger('HPub', logging.INFO)


class HDKafkapRepSrv(HDaemonRepSrv):
    def __init__(self, port, run_data, pub_metrics):
        self.run_data = run_data
        self.pub_metrics = pub_metrics
        self.init_pub_metrics()
        HDaemonRepSrv.__init__(self, port)
        self.register_fn('teststart', self.test_start)
        self.register_fn('getstats', self.get_stats)
        self.register_fn('teststatus', self.test_status)
        self.register_fn('updateconfig', self.update_config)

    def test_start(self):
        process = psutil.Process()
        self.run_data['start'] = True
        self.run_data['test_status'] = 'running'
        self.run_data['stats'] = {'net:start': json.dumps(psutil.net_io_counters()),
                                  'cpu:start': json.dumps(process.cpu_times()),
                                  'mem:start': json.dumps(process.memory_info()),
                                  'time:start': json.dumps(time.time())}
        return ('ok', None)

    def get_stats(self):
        l.info("Sending Stats:" + pformat(self.run_data['stats']))
        return ('ok', self.run_data['stats'])

    def test_status(self):
        return ('ok', self.run_data['test_status'])

    def init_pub_metrics(self):
        l.info("Init PUB metrics...")
        self.test_duration = self.pub_metrics['test_duration']
        self.msg_batch = self.pub_metrics['msg_batch']
        self.msg_requested_rate = self.pub_metrics['msg_requested_rate']

    def update_config(self, test_duration, msg_batch, msg_requested_rate):
        self.test_duration = float(test_duration)
        self.msg_batch = int(msg_batch)
        self.msg_requested_rate = float(msg_requested_rate)
        l.info("PUB updated metrics: test_duration=%f, msg_batch=%f, msg_requested_rate=%f", self.test_duration,
               self.msg_batch, self.msg_requested_rate)
        return ('ok', None)


def run(argv):
    if len(argv) > 4:
        test_duration = argv[1]
        msg_batch = argv[2]
        msg_requested_rate = argv[3]
        topic_name = argv[4]
        acks = argv[5]
        linger_ms = argv[6]
        msg_batch = int(msg_batch)
        msg_requested_rate = float(msg_requested_rate)
        test_duration = float(test_duration)
        topic_name = str(topic_name)
        acks = int(acks)
        linger_ms = int(linger_ms)


    # Initialize Kafka PUB Server
    l.info("Starting Kafka Publisher (producer)")
    # Estimate average message size to compute batch_size in [bytes] / Requested by Kafka
    min_message_size = len(str(0) + ' msg' + str(0))
    max_message_size = len(str(msg_requested_rate) + ' msg' + str(msg_requested_rate))
    average_message_size = (min_message_size + max_message_size) / 2
    batch_estimated_size = (average_message_size) * msg_batch
    producer = KafkaProducer(bootstrap_servers='localhost:9092', batch_size=batch_estimated_size, linger_ms=linger_ms, acks=acks)

    # Initialize simple Rep server, this is used to listen
    # for the signal to start sending data
    pub_rep_port = os.environ.get('PORT0')
    l.info("STARTING KAFKA REP server at port [%s].", pub_rep_port)
    run_data = {'start': False,
                'stats': {'rate': 0, 'msg_cnt': 0},
                'test_status': 'stopped'}
    pub_metrics = {'test_duration': test_duration,
                   'msg_batch': msg_batch,
                   'msg_requested_rate': msg_requested_rate}
    hd = HDKafkapRepSrv(pub_rep_port, run_data, pub_metrics)
    hd.run()

    while True:
        #  Wait for 'signal' to start sending messages to Kafka Broker
        if not run_data['start']:
            l.debug("KAFKA PUB WAITING FOR SIGNAL...")
            time.sleep(1)
            continue
        l.info('PUB server initiating... Test Duration [%f] secs. Messages with batches [%d]'
               'and requested msg rate [%f]' % (hd.test_duration, hd.msg_batch, hd.msg_requested_rate))
        cnt = 0
        msg_cnt = 0
        start_time = time.time()

        # Start Publishing Messages to Broker
        while True:
            # Build 'message'
            messagedata = "msg%d" % msg_cnt
            message = "%d %s" % (msg_cnt, messagedata)

            try:
                # Publish message to the Kafka Cluster
                # topic: specifies the 'topic' where the message will be published
                producer.send(topic=topic_name, value=message)
            except KafkaTimeoutError as e:
                l.error("Unable to publish message to the Kafka Cluster. ERROR: %s" % e.message)

            # Insert a 'delay' if tx rate between batches outperforms the expected
            # (minimum) rate to achieve requested tx rate
            cnt += 1
            msg_cnt += 1
            if cnt >= hd.msg_batch:
                # Compute the delay
                duration = time.time() - start_time
                expected_time = msg_cnt / hd.msg_requested_rate
                delay = 0.0
                if expected_time > duration:
                    delay = expected_time - duration
                if delay > 1:
                    delay = 1
                time.sleep(delay)
                cnt = 0
            elapsed_time = time.time() - start_time
            if elapsed_time >= hd.test_duration:
                break
        # Update 'stats' to 'hd' (HDaemon)
        run_data['stats']['time:end'] = json.dumps(time.time())
        run_data['stats']['rate'] = msg_cnt / elapsed_time
        run_data['stats']['msg_cnt'] = msg_cnt
        process = psutil.Process()
        run_data['stats']['net:end'] = json.dumps(psutil.net_io_counters())
        run_data['stats']['cpu:end'] = json.dumps(process.cpu_times())
        run_data['stats']['mem:end'] = json.dumps(process.memory_info())
        run_data['test_status'] = 'stopping'
        # Go back to waiting for the next test
        run_data['start'] = False
        producer.close()
        l.info("PUB Server stopping after sending %d messages elapsed time %f and message rate %f" %
               (msg_cnt, elapsed_time, run_data['stats']['rate']))
        break
