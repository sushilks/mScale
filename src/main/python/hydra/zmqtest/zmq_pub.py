__author__ = 'sushil, abdullahS'

import zmq
import time
import logging
import os
from pprint import pprint, pformat   # NOQA
from hydra.lib import util
from hydra.lib.hdaemon import HDaemonRepSrv
l = util.createlogger('HPub', logging.INFO)


class HDZmqpRepSrv(HDaemonRepSrv):
    def __init__(self, port, run_data):
        self.run_data = run_data
        HDaemonRepSrv.__init__(self, port)
        self.register_fn('start', self.start_test)
        self.register_fn('stats', self.get_stats)
        self.register_fn('teststatus', self.test_status)

    def start_test(self, args):
        self.run_data['start'] = True
        return ('ok', None)

    def get_stats(self, args):
        return ('ok', self.run_data['stats'])

    def test_status(self, args):
        return ('ok', self.run_data['test_status'])


def run(argv):
    pub_port = "15556"  # accept it as an argument PORT1
    if len(argv) > 3:
        test_duration = argv[1]
        msg_batch = argv[2]
        msg_requested_rate = argv[3]
        msg_batch = int(msg_batch)
        msg_requested_rate = float(msg_requested_rate)
        test_duration = float(test_duration)

    # init and bind pub server
    pub_context = zmq.Context()
    pub_socket = pub_context.socket(zmq.PUB)
    pub_socket.bind("tcp://*:%s" % pub_port)

    # init simple zmq rep server, this is used to listen
    # for the signal to start sending data
    pub_rep_port = os.environ.get('PORT0')
    l.info("Starting zmq REP server at port [%s]", pub_rep_port)
    run_data = {'start': False,
                'stats': {'rate': 0, 'count': 0},
                'test_status': False}
    hd = HDZmqpRepSrv(pub_rep_port, run_data)
    hd.run()
    # pub_rep_context = zmq.Context()
    # pub_rep_socket = pub_rep_context.socket(zmq.REP)
    # pub_rep_socket.bind("tcp://*:%s" % pub_rep_port)
    # l.info("Done Binding zmq REP socket...")
    while True:
        if not run_data['start']:
            time.sleep(1)
            continue
        l.info("PUB server initiating test_duration [%f] messages, with batches [%d] with msg rate[%f]",
               test_duration, msg_batch, msg_requested_rate)
        cnt = 0
        msg_cnt = 0
        start_time = time.time()
        while True:
            messagedata = "msg%d" % msg_cnt
            # l.info("%d %s" % (index, messagedata))
            pub_socket.send("%d %s" % (msg_cnt, messagedata))
            cnt += 1
            msg_cnt += 1
            if cnt >= msg_batch:
                # compute the delay
                duration = time.time() - start_time
                expected_time = msg_cnt / msg_requested_rate
                delay = 0.0
                if expected_time > duration:
                    delay = expected_time - duration
                if delay > 1:
                    delay = 1
                time.sleep(delay)
                cnt = 0
            elapsed_time = time.time() - start_time
            if elapsed_time >= test_duration:
                break
        run_data['stats']['rate'] = msg_cnt / elapsed_time
        run_data['stats']['count'] = msg_cnt
        run_data['test_status'] = True
        pub_socket.close()
        l.info("PUB Server stopping after sending %d messages elapsed time %f and message rate %f" %
               (msg_cnt, elapsed_time, run_data['stats']['rate']))
        break
