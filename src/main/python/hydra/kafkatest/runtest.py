__author__ = 'annyz'

import sys
from pprint import pprint, pformat  # NOQA
from optparse import OptionParser
import logging
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

tout_60s = 60000
tout_30s = 30000
tout_10s = 10000


class KAFKAPubAnalyser(HAnalyser):
    def __init__(self, server_ip, server_port, task_id):
        HAnalyser.__init__(self, server_ip, server_port, task_id)


class KAFKASubAnalyser(HAnalyser):
    def __init__(self, server_ip, server_port):
        HAnalyser.__init__(self, server_ip, server_port)


class RunTestKAFKA(RunTestBase):
    def __init__(self, options, runtest=True, mock=False):

        self.options = options          # Object contains 'options' parsed from the Command-Line Interface
        self.config = ConfigParser()    # Object contains 'configurations' parsed from hydra.ini config file

        RunTestBase.__init__(self, 'KAFKAScale', self.options, self.config, startappserver=runtest, mock=mock)
        self.kafkapub = self.format_appname('/kafka-pub')
        self.kafkasub = self.format_appname('/kafka-sub')
        self.add_appid(self.kafkapub)
        self.add_appid(self.kafkasub)
        self.boundary_setup(self.options, 'msg_rate', self.boundary_resultfn)
        if runtest:
            self.run_test()
            self.stop_appserver()

    def rerun_test(self, options):
        self.options = options
        self.boundary_setup(self.options, 'msg_rate', self.boundary_resultfn)

        l.info("Updating test metrics: test_duration=%s, msg_batch=%s, msg_rate=%s",
               self.options.test_duration, self.options.msg_batch, self.options.msg_rate)

        # Update the PUB server with new metrics
        self.ha_pub.update_config(test_duration=self.options.test_duration,
                                  msg_batch=self.options.msg_batch,
                                  msg_requested_rate=self.options.msg_rate)
        l.info("PUB server updated")

        self.reset_all_app_stats(self.kafkasub)

        # Signal message sending
        l.info("Sending signal to PUB to start sending all messages..")
        self.ha_pub.start_test()
        self.ha_pub.wait_for_testend()
        self.fetch_app_stats(self.kafkapub)
        assert(len(self.apps[self.kafkapub]['stats']) == 1)
        pub_data = self.apps[self.kafkapub]['stats'].values()[0]
        l.info("Publisher send %d packets at the rate of %d pps" % (pub_data['msg_cnt'],
                                                                    pub_data['rate']))

        # Fetch all sub client data
        self.fetch_app_stats(self.kafkasub)

        return self.result_parser()

    def run_test(self, first_run=True):
        self.start_init()
        if hasattr(self, 'sub_app_ip_rep_port_map'):
            # If Sub's have been launched Reset first
            self.reset_all_app_stats(self.kafkasub)
        topic_name = self.get_topic_name()
        # Launch Kafka Pub App
        self.launch_kafka_pub(topic_name)
        # Launch Kafka Sub App(s)
        self.launch_kafka_sub(topic_name)
        # Rerun Kafka Test
        res = self.rerun_test(self.options)

        return res

    def get_topic_name(self):
        return 'topic_' + str(self.options.total_sub_apps) + '_' + str(self.options.msg_rate) + '_' \
               + str(self.options.msg_batch)

    def boundary_resultfn(self, options, res):
        message_rate = options.msg_rate
        l.info("Completed run with message rate = %d and client count=%d " %
               (message_rate, options.total_sub_apps * 10) +
               "Reported Rate PUB:%f SUB:%f and Reported Drop Percentage : %f" %
               (res['average_tx_rate'], res['average_rate'], res['average_packet_loss']))
        l.info("\t\tCompleted-2: Pub-CPU:%3f%% PUB-TX:%.2fMbps PUB-RX:%.2fMbps " %
               (res['pub_cpu'], res['pub_net_txrate'] / 1e6, res['pub_net_rxrate'] / 1e6))
        run_pass = True
        if (res['average_tx_rate'] < 0.7 * message_rate):
            # if we are unable to get 70% of the tx rate
            run_pass = False
        return (run_pass, res['average_rate'], res['average_packet_loss'])

    def stop_and_delete_all_apps(self):
        self.delete_all_launched_apps()

    def result_parser(self):
        result = {
            'client_count': 0,
            'average_packets': 0,
            'average_rate': 0,
            'failing_clients': 0,
            'average_packet_loss': 0
        }
        pub_data = self.apps[self.kafkapub]['stats'].values()[0]
        msg_cnt_pub_tx = pub_data['msg_cnt']
        bad_clients = 0
        client_rate = 0
        bad_client_rate = 0
        clients_packet_count = 0
        stats = self.get_app_stats(self.kafkasub)
        num_subs = len(stats)

        for client in stats.keys():
            info = stats[client]
            client_rate += info['rate']
            clients_packet_count += info['msg_cnt']
            if info['msg_cnt'] != msg_cnt_pub_tx:
                l.info("[%s] Count Mismatch Info: %s" % (client, pformat(info)))
                bad_clients += 1
                bad_client_rate += info['rate']
        if bad_clients > 0:
            l.info("Total number of clients experiencing packet drop = %d out of %d clients" %
                   (bad_clients, num_subs))
            l.info('Average rate seen at the failing clients %f' % (bad_client_rate / bad_clients))
        else:
            l.info("No client experienced packet drops out of %d clients" % num_subs)
        l.info("Total packet's send by PUB:%d and average packets received by client:%d" %
               (msg_cnt_pub_tx, clients_packet_count / num_subs))
        l.info('Average rate seen at the pub %f and at clients %f' %
               (pub_data['rate'], (client_rate / num_subs)))
        result['client_count'] = num_subs
        result['packet_tx'] = msg_cnt_pub_tx
        result['average_packets'] = clients_packet_count / result['client_count']
        result['average_rate'] = client_rate / result['client_count']
        result['failing_clients'] = bad_clients
        result['average_tx_rate'] = pub_data['rate']
        if bad_clients:
            result['failing_clients_rate'] = (bad_client_rate / bad_clients)
        result['average_packet_loss'] = \
            ((msg_cnt_pub_tx - (1.0 * clients_packet_count / result['client_count'])) * 100.0 / msg_cnt_pub_tx)
        if 'cpu:start' in pub_data:
            pub_total_cpu = (pub_data['cpu:end'][0] + pub_data['cpu:end'][1] -
                             (pub_data['cpu:start'][0] + pub_data['cpu:start'][1]))
        else:
            pub_total_cpu = 0
        pub_total_time = pub_data['time:end'] - pub_data['time:start']
        if 'net:start' in pub_data:
            pub_total_nw_txbytes = pub_data['net:end'][0] - pub_data['net:start'][0]
            pub_total_nw_rxbytes = pub_data['net:end'][1] - pub_data['net:start'][1]
        else:
            pub_total_nw_rxbytes = pub_total_nw_txbytes = 0
        result['pub_cpu'] = 100.0 * pub_total_cpu / pub_total_time
        result['pub_net_txrate'] = pub_total_nw_txbytes / pub_total_time
        result['pub_net_rxrate'] = pub_total_nw_rxbytes / pub_total_time
        l.debug(" RESULTS on TEST = " + pformat(result))
        return result

    def launch_kafka_pub(self, topic_name):
        l.info("Launching the KAFKA PUB app...")
        # Define Marathon Constraints to define where apps should run for optimization
        constraints = [self.app_constraints(field='hostname', operator='UNIQUE')]

        # Use cluster0 for launching the PUB
        if 0 in self.mesos_cluster:
            l.info('Constraint Attribute to match: [%s] Value to match: [%s]' % (self.mesos_cluster[0]['cat'],
                                                                                 self.mesos_cluster[0]['match']))
            constraints.append(self.app_constraints(field=self.mesos_cluster[0]['cat'],
                                                    operator='CLUSTER', value=self.mesos_cluster[0]['match']))
        self.create_hydra_app(name=self.kafkapub, app_path='hydra.kafkatest.kafka_pub.run',
                              app_args='%s %s %s %s %s %s' % (self.options.test_duration,
                                                              self.options.msg_batch,
                                                              self.options.msg_rate,
                                                              topic_name,
                                                              self.options.acks,
                                                              self.options.linger_ms),
                              cpus=0.01, mem=32,
                              ports=[0],
                              constraints=constraints)
        ipm = self.get_app_ipport_map(self.kafkapub)
        assert(len(ipm) == 1)
        self.pub_ip = ipm.values()[0][1]
        self.pub_rep_taskport = str(ipm.values()[0][0])

        l.info("[KafkaTest.launch_pub] KAFKA pub server running at [%s]", self.pub_ip)
        l.info("[KafkaTest.launch_pub] KAFKA REP server running at [%s:%s]", self.pub_ip, self.pub_rep_taskport)

        # Initialize KAFKAPubAnalyser (to control & collect stats from test instances)
        self.ha_pub = KAFKAPubAnalyser(self.pub_ip, self.pub_rep_taskport, ipm.keys()[0])

    def launch_kafka_sub(self, topic_name):
        l.info("[KafkaTest.launch_sub] Launching KAFKA sub app...")
        constraints = []
        # Use cluster 1 for launching the SUB (control where the SUB apps will run)
        if 1 in self.mesos_cluster:
            constraints.append(self.app_constraints(field=self.mesos_cluster[1]['cat'],
                                                    operator='CLUSTER', value=self.mesos_cluster[1]['match']))
        self.create_hydra_app(name=self.kafkasub, app_path='hydra.kafkatest.kafka_sub.run10',
                              app_args='%s %s %s' % (topic_name, self.pub_ip,
                                                     self.options.consumer_max_buffer_size),
                              cpus=0.01, mem=32,
                              ports=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                              constraints=constraints)
        # Scale KAFKA Sub App
        self.scale_sub_app()

    def scale_sub_app(self):
        self.scale_and_verify_app(self.kafkasub, self.options.total_sub_apps)

    def delete_all_launched_apps(self):
        l.info("[KafkaTest.delete_all_launched_apps] Deleting ALL (PUB & SUBs) launched apps")
        l.info("[KafkaTest.delete_all_launched_apps] (1/2) Deleting PUB")
        self.delete_app(self.kafkapub)
        l.info("[KafkaTest.delete_all_launched_apps] (2/2) Deleting SUBs")
        self.delete_app(self.kafkasub)


class RunTest(object):
    def __init__(self, argv):
        usage = ('python %prog --test_duration=<time to run test> --msg_batch=<msg burst batch before sleep>'
                 '--msg_rate=<rate in packet per secs> --total_sub_apps=<Total sub apps to launch>'
                 '--config_file=<path_to_config_file> --keep_running'
                 '--acks=<server_acknowledgement> --linger_ms=<linger_ms>'
                 '--consumer_max_buffer_size=<consumer_buffer_size>')
        # Parse Command-Line options and set to default values if not specified
        parser = OptionParser(description='kafka scale test master',
                              version="0.1", usage=usage)
        parser.add_option("--test_duration", dest='test_duration', type='float', default=10)
        parser.add_option("--msg_batch", dest='msg_batch', type='int', default=100)
        parser.add_option("--msg_rate", dest='msg_rate', type='float', default=10000)
        parser.add_option("--total_sub_apps", dest='total_sub_apps', type='int', default=20)
        parser.add_option("--config_file", dest='config_file', type='string', default='hydra.ini')
        parser.add_option("--keep_running", dest='keep_running', action="store_true", default=False)
        # Kafka-related configuration parameters
        # parser.add_option("--fetch_min_bytes", dest='fetch_min_bytes', type='int', default=1)
        # parser.add_option("--fetch_wait_max_ms", dest='fetch_wait_max_ms', type='int', default=100)
        parser.add_option("--acks", dest='acks', type='int', default=1)
        parser.add_option("--linger_ms", dest='linger_ms', type='int', default=0)
        parser.add_option("--consumer_max_buffer_size", dest='consumer_max_buffer_size', type='int', default=0)

        (options, args) = parser.parse_args()
        if ((len(args) != 0)):
            parser.print_help()
            sys.exit(1)
        r = RunTestKAFKA(options, False)      # Initialize ALL variables (from CLI options and hydra.ini config file)
        r.start_appserver()
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
