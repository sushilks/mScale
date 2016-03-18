__author__ = 'sushil, abdullahS'

import sys
from pprint import pprint, pformat  # NOQA
from optparse import OptionParser
import logging
import time
from hydra.lib import util
from hydra.lib.h_analyser import HAnalyser
from hydra.lib.runtestbase import RunTestBase
try:
    # Python 2.x
    from ConfigParser import ConfigParser
except ImportError:
    # Python 3.x
    from configparser import ConfigParser

l = util.createlogger('runTest', logging.INFO)
# l.setLevel(logging.DEBUG)

tout_60s = 30000
tout_30s = 30000
tout_10s = 10000


class ZMQPubAnalyser(HAnalyser):
    def __init__(self, server_ip, server_port):
        HAnalyser.__init__(self, server_ip, server_port)

    def start_test(self):
        # TODO: (AbdullahS): Make sure pub actually started sending data
        l.info("Sending Start test to PUB")
        (status, resp) = self.do_req_resp('start', timeout=tout_60s)
        l.info("Start test came back with status " + pformat(status) + " resp = " + pformat(resp))
        assert(status == 'ok')

    def wait_for_testend(self):
        while True:
            (status, resp) = self.do_req_resp('teststatus', tout_30s)
            assert(status == 'ok')
            if resp:
                break
            time.sleep(1)

    def get_stats(self):
        (status, resp) = self.do_req_resp('stats')
        assert(status == 'ok')
        return resp

    def update_pub_metrics(self, pub_metrics={}):
        (status, resp) = self.do_req_resp('updatepub', msg_args=pub_metrics)
        assert(status == 'ok')
        return resp


class ZMQSubAnalyser(HAnalyser):
    def __init__(self, server_ip, server_port):
        HAnalyser.__init__(self, server_ip, server_port)

    def get_stats(self):
        (status, resp) = self.do_req_resp('stats', 0)
        assert(status == 'ok')
        return resp

    def reset_stats(self):
        (status, resp) = self.do_req_resp('reset', 0)
        assert(status == 'ok')
        return resp


class RunTestZMQ(RunTestBase):
    def __init__(self, options, runtest=True):
        self.test_duration = options.test_duration
        self.msg_batch = options.msg_batch
        self.msg_rate = options.msg_rate
        self.total_sub_apps = options.total_sub_apps
        self.config_file = options.config_file
        self.keep_running = options.keep_running

        self.config = ConfigParser()
        config_fn = self.config_file
        RunTestBase.__init__(self, 'zmqScale', self.config, config_fn, startappserver=runtest)
        self.zstpub = '/zst-pub'
        self.zstsub = '/zst-sub'
        self.add_appid(self.zstpub)
        self.add_appid(self.zstsub)
        if runtest:
            self.run_test()
            self.stop_appserver()

    def update_metrics_run_test(self, options):
        self.test_duration = options.test_duration
        self.msg_batch = options.msg_batch
        self.msg_rate = options.msg_rate
        l.info("Updating test metrics: test_duration=%s, msg_batch=%s, msg_rate=%s",
               self.test_duration, self.msg_batch, self.msg_rate)

        # Update the PUB server with new metrics
        pub_metrics = {'test_duration': self.test_duration,
                       'msg_batch': self.msg_batch,
                       'msg_requested_rate': self.msg_rate}
        self.ha_pub.update_pub_metrics(pub_metrics)
        l.info("PUB server updated")

        # Reset all clients stats
        # TODO: (ABdullahS): Make this more intelligent in next step
        #                    i-e add scaling up and down
        self.reset_sub_stats(self.sub_app_ip_rep_port_map)

        # Signal message sending
        pub_data = self.signal_pub_send_msgs()
        l.info("Publisher send %d packets at the rate of %d pps" % (pub_data['count'],
                                                                    pub_data['rate']))

        # Fetch all sub client data
        self.fetch_all_sub_clients_data()

        all_clients = self.all_sub_clients_info.items()
        return self.result_parser(all_clients, pub_data)

    def run_test(self, start_appserver=True):
        self.start_init()
        if start_appserver:
            self.start_appserver()
        res = self.start_test()
        return res

    def stop_and_delete_all_apps(self):
        self.delete_all_launched_apps()

    def start_test(self):
        # Launch zmq pub
        self.launch_zmq_pub()

        # Launch zmq sub up to self.total_sub_apps
        self.launch_zmq_sub()

        # probe all the clients to see if they are ready.
        self.ping_all_sub()

        # Signal PUB to start sending all messages, blocks until PUB notifies
        pub_data = self.signal_pub_send_msgs()
        l.info("Publisher send %d packets at the rate of %d pps" % (pub_data['count'],
                                                                    pub_data['rate']))

        #  Fetch all client SUB data
        self.fetch_all_sub_clients_data()

        l.info("Successfully finished gathering all data")

        all_clients = self.all_sub_clients_info.items()
        return self.result_parser(all_clients, pub_data)

    def result_parser(self, all_clients, pub_data):
        result = {
            'client_count': 0,
            'average_packets': 0,
            'average_rate': 0,
            'failing_clients': 0,
            'average_packet_loss': 0
        }
        msg_cnt_pub_tx = pub_data['count']
        bad_clients = 0
        client_rate = 0
        bad_client_rate = 0
        clients_packet_count = 0
        for client, info in all_clients:
            # l.info(" CLIENT = " + pformat(client) + " DATA = " + pformat(info))
            client_rate += info['rate']
            clients_packet_count += info['msg_cnt']
            if info['msg_cnt'] != msg_cnt_pub_tx:
                l.info("[%s] Count Mismatch Info: %s" % (client, pformat(info)))
                bad_clients += 1
                bad_client_rate += info['rate']
        if bad_clients > 0:
            l.info("Total number of clients experiencing packet drop = %d out of %d clients" %
                   (bad_clients, len(all_clients)))
            l.info('Average rate seen at the failing clients %f' % (bad_client_rate / bad_clients))
        else:
            l.info("No client experienced packet drops out of %d clients" % len(all_clients))
        l.info("Total packet's send by PUB:%d and average packets received by client:%d" %
               (msg_cnt_pub_tx, clients_packet_count / len(all_clients)))
        l.info('Average rate seen at the pub %f and at clients %f' %
               (pub_data['rate'], (client_rate / len(all_clients))))
        result['client_count'] = len(all_clients)
        result['packet_tx'] = msg_cnt_pub_tx
        result['average_packets'] = clients_packet_count / result['client_count']
        result['average_rate'] = client_rate / result['client_count']
        result['failing_clients'] = bad_clients
        result['average_tx_rate'] = pub_data['rate']
        if bad_clients:
            result['failing_clients_rate'] = (bad_client_rate / bad_clients)
        result['average_packet_loss'] = \
            ((msg_cnt_pub_tx - (1.0 * clients_packet_count / result['client_count'])) * 100.0 / msg_cnt_pub_tx)
        return result

    def launch_zmq_pub(self):
        l.info("Launching the pub app")
        constraints = [self.app_constraints(field='hostname', operator='UNIQUE')]
        # Use cluster0 for launching the PUB
        if 0 in self.mesos_cluster:
            constraints.append(self.app_constraints(field=self.mesos_cluster[0]['cat'],
                                                    operator='CLUSTER', value=self.mesos_cluster[0]['match']))
        self.create_hydra_app(name=self.zstpub, app_path='hydra.zmqtest.zmq_pub.run',
                              app_args='%s %s %s %s' % (self.test_duration,
                                                        self.msg_batch,
                                                        self.msg_rate, self.total_sub_apps),
                              cpus=0.01, mem=32,
                              ports=[0],
                              constraints=constraints)
        self.wait_app_ready(self.zstpub, 1)
        # Find launched pub server's ip, rep PORT
        self.pub_ip = self.find_ip_uniqueapp(self.zstpub)
        tasks = self.get_app_tasks(self.zstpub)
        assert(len(tasks) == 1)
        assert(len(tasks[0].ports) == 1)
        self.pub_rep_taskport = str(tasks[0].ports[0])
        l.info("[zmq_pub] ZMQ pub server running at [%s]", self.pub_ip)
        l.info("[zmq_pub] ZMQ REP server running at [%s:%s]", self.pub_ip, self.pub_rep_taskport)
        # Init ZMQPubAnalyser
        self.ha_pub = ZMQPubAnalyser(self.pub_ip, self.pub_rep_taskport)

    def launch_zmq_sub(self):
        l.info("Launching the sub app")
        constraints = []
        # Use cluster 1 for launching the SUB
        if 1 in self.mesos_cluster:
            constraints.append(self.app_constraints(field=self.mesos_cluster[1]['cat'],
                                                    operator='CLUSTER', value=self.mesos_cluster[1]['match']))
        self.create_hydra_app(name=self.zstsub, app_path='hydra.zmqtest.zmq_sub.run10',
                              app_args='%s 15556' % (self.pub_ip),  # pub_ip, pub_port
                              cpus=0.01, mem=32,
                              ports=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                              constraints=constraints)
        self.wait_app_ready(self.zstsub, 1)

        # scale
        l.info("Scaling sub app to [%d]", self.total_sub_apps)
        self.scale_app(self.zstsub, self.total_sub_apps)
        self.wait_app_ready(self.zstsub, self.total_sub_apps)

        # Extract ip, rep server port for data querying
        self.sub_app_ip_rep_port_map = {}  # key = task.id, value= {port: ip}
        tasks = self.get_app_tasks(self.zstsub)
        assert(len(tasks) == self.total_sub_apps)
        for task in tasks:
            sub_app_ip = self.get_ip_hostname(task.host)
            for sub_app_rep_port in task.ports:
                self.sub_app_ip_rep_port_map[task.id + '_PORT' + str(sub_app_rep_port)] = \
                    [sub_app_rep_port, sub_app_ip]
        # l.info(self.sub_app_ip_rep_port_map)

    def signal_pub_send_msgs(self):
        l.info("Sending signal to PUB to start sending all messages..")
        # Signal it to start sending data, blocks until PUB responsds with "DONE" after sending all data
        self.ha_pub.start_test()
        self.ha_pub.wait_for_testend()
        return self.ha_pub.get_stats()

    def fetch_all_sub_clients_data(self):
        l.info("Attempting to fetch all client data..")
        # TODO: (AbdullahS): Add more stuff, timestamp, client ip etc
        self.all_sub_clients_info = {}  # stores a mapping of client_id: {msg_count: x}
        for task_id, info in self.sub_app_ip_rep_port_map.items():
            port = info[0]
            ip = info[1]
            ha_sub = ZMQSubAnalyser(ip, port)
            # Signal it to start sending data, blocks until PUB responsds with "DONE" after sending all data
            stats = ha_sub.get_stats()
            ha_sub.stop()  # closes the ANalyser socket, can not be used anymore
            self.all_sub_clients_info[str(ip) + ':' + str(port)] = stats

    def ping_all_sub(self):
        l.info('Pinging all the clients to make sure they are started....')
        cnt = 0
        remove_list = []
        for task_id, info in self.sub_app_ip_rep_port_map.items():
            port = info[0]
            ip = info[1]
            ha = HAnalyser(ip, port)
            # Signal it to start sending data, blocks until PUB responsds with "DONE" after sending all data
            res = ha.do_ping()
            if not res:
                l.info("Ping failed to [%s] %s:%s. removing from client list" % (task_id, ip, port))
                remove_list.append(task_id)
            cnt += res
            ha.stop()  # closes the ANalyser socket, can not be used anymore

        for item in remove_list:
            del self.sub_app_ip_rep_port_map[item]
        l.info('Done pinging all the clients. Got pong response from %d out of %d' %
               (cnt, len(self.sub_app_ip_rep_port_map.items())))

    def reset_sub_stats(self, sub_app_ip_rep_port_map):
        l.info("Attempting to reset client stats ...")
        for task_id, info in sub_app_ip_rep_port_map.items():
            port = info[0]
            ip = info[1]
            ha_sub = ZMQSubAnalyser(ip, port)
            # Signal it to reset all client stats
            l.debug("Resetting stats for %s:%s", ip, port)
            ha_sub.reset_stats()
            ha_sub.stop()  # closes the ANalyser socket, can not be used anymore

    def delete_all_launched_apps(self):
        l.info("Deleting all launched apps")
        l.info("Deleting PUB")
        self.delete_app(self.zstpub)
        l.info("Deleting SUBs")
        self.delete_app(self.zstsub)


class RunTest(object):
    def __init__(self, argv):
        usage = ('python %prog --test_duration=<time to run test> --msg_batch=<msg burst batch before sleep>'
                 '--msg_rate=<rate in packet per secs> --total_sub_apps=<Total sub apps to launch>'
                 '--config_file=<path_to_config_file> --keep_running')
        parser = OptionParser(description='zmq scale test master',
                              version="0.1", usage=usage)
        parser.add_option("--test_duration", dest='test_duration', type='float', default=10)
        parser.add_option("--msg_batch", dest='msg_batch', type='int', default=100)
        parser.add_option("--msg_rate", dest='msg_rate', type='float', default=10000)
        parser.add_option("--total_sub_apps", dest='total_sub_apps', type='int', default=100)
        parser.add_option("--config_file", dest='config_file', type='string', default='hydra.ini')
        parser.add_option("--keep_running", dest='keep_running', action="store_true", default=False)

        (options, args) = parser.parse_args()
        if ((len(args) != 0)):
            parser.print_help()
            sys.exit(1)
        r = RunTestZMQ(options, False)
        res = r.run_test()
        r.delete_all_launched_apps()
        print("RES = " + pformat(res))
        if not options.keep_running:
            r.stop_appserver()
        else:
            print("Keep running is set: Leaving the app server running")
            print("   you can use the marathon gui/cli to scale the app up.")
            print("   after you are done press enter on this window")
            input('>')
            r.stop_appserver()
