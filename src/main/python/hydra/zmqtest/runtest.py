__author__ = 'sushil, abdullahS'

import sys
from pprint import pprint, pformat  # NOQA
from optparse import OptionParser
import logging
from sets import Set
from hydra.lib import util
from hydra.lib.h_analyser import HAnalyser
from hydra.lib.hydrabase import HydraBase
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


class ZMQPubAnalyser(HAnalyser):
    def __init__(self, server_ip, server_port, task_id):
        HAnalyser.__init__(self, server_ip, server_port, task_id)


class ZMQSubAnalyser(HAnalyser):
    def __init__(self, server_ip, server_port, task_id):
        HAnalyser.__init__(self, server_ip, server_port, task_id)


class RunTestZMQ(HydraBase):
    def __init__(self, options, runtest=True):
        # self.options = options
        # self.test_duration = options.test_duration
        # self.msg_batch = options.msg_batch
        # self.msg_rate = options.msg_rate
        # self.total_sub_apps = options.total_sub_apps
        # self.config_file = options.config_file
        # self.keep_running = options.keep_running

        self.config = ConfigParser()
        HydraBase.__init__(self, 'zmqScale', options, self.config, startappserver=runtest)
        self.zstpub = self.format_appname('/zst-pub')
        self.zstsub = self.format_appname('/zst-sub')
        self.add_appid(self.zstpub)
        self.add_appid(self.zstsub)
        self.boundary_setup(self.options, 'msg_rate', self.boundary_resultfn)
        if runtest:
            self.run_test()
            self.stop_appserver()

    def rerun_test(self, options):
        self.set_options(options)
        self.boundary_setup(self.options, 'msg_rate', self.boundary_resultfn)
        # self.test_duration = options.test_duration
        # self.msg_batch = options.msg_batch
        # self.msg_rate = options.msg_rate
        l.info("Updating test metrics: test_duration=%s, msg_batch=%s, msg_rate=%s",
               self.options.test_duration, self.options.msg_batch, self.options.msg_rate)

        # Update the PUB server with new metrics
        self.ha_pub.update_config(test_duration=self.options.test_duration,
                                  msg_batch=self.options.msg_batch,
                                  msg_requested_rate=self.options.msg_rate)
        l.info("PUB server updated")

        self.reset_all_app_stats(self.zstsub)
        # Select which sub's are going to be slow
        # and send them there rate.
        # add the properties to the sub app data structure on their rate.
        acnt = self.get_app_instcnt(self.zstsub)
        slow_num = int(acnt * options.slow_clients_percent / 100)
        update_sub_config = False
        if slow_num:
            slow_clients = self.get_app_property(self.zstsub, 'slow_clients')
            if not slow_clients or int(slow_num) != len(slow_clients):
                # reset all the clients
                self.set_app_property(self.zstsub, 'slow_clients',
                                      Set(self.random_select_instances(self.zstsub, slow_num)))
                update_sub_config = True
        rec_num = int(acnt * options.rec_clients_percent / 100)
        if rec_num:
            rec_clients = self.get_app_property(self.zstsub, 'reconnecting_clients')
            if not rec_clients or rec_num != len(rec_clients):
                self.set_app_property(self.zstsub, 'reconnecting_clients',
                                      Set(self.random_select_instances(self.zstsub, rec_num)))
                update_sub_config = True
        if update_sub_config:
            # Now update all the slow clients
            ipm = self.get_app_ipport_map(self.zstsub)
            slow_set = self.get_app_property(self.zstsub, 'slow_clients')
            rec_set = self.get_app_property(self.zstsub, 'reconnecting_clients')
            for key in ipm.keys():
                ip = ipm[key][1]
                port = ipm[key][0]
                ha = HAnalyser(ip, port, key)
                recv_rate = 0
                reconnect_rate = 0
                if slow_set and key in slow_set:
                    print("Task ID " + key + " Is going to be slow")
                    recv_rate = options.slow_clients_rate
                if rec_set and key in rec_set:
                    print("Task ID " + key + " Is going to be reconnecting")
                    reconnect_rate = options.rec_clients_rate
                ha.update_config(recv_rate=recv_rate, reconnect_rate=reconnect_rate)
                ha.stop()

        # Signal message sending
        l.info("Sending signal to PUB to start sending all messages..")
        self.ha_pub.start_test()
        self.ha_pub.wait_for_testend()
        self.fetch_app_stats(self.zstpub)
        assert(len(self.apps[self.zstpub]['stats']) == 1)
        pub_data = self.apps[self.zstpub]['stats'].values()[0]
        l.info("Publisher send %d packets at the rate of %d pps" % (pub_data['msg_cnt'],
                                                                    pub_data['rate']))

        # Fetch all sub client data
        self.fetch_app_stats(self.zstsub)

        return self.result_parser()

    def run_test(self, first_run=True):
        self.start_init()
        if hasattr(self, 'sub_app_ip_rep_port_map'):
            # If Sub's have been launched Reset first
            self.reset_all_app_stats(self.zstsub)
        self.launch_zmq_pub()
        # Launch zmq sub up to self.total_sub_apps
        self.launch_zmq_sub()
        res = self.rerun_test(self.options)
        return res

    def boundary_resultfn(self, options, res):
        message_rate = options.msg_rate
        l.info("Completed run with message rate = %d and client count=%d/%d " %
               (message_rate, options.total_sub_apps * 10, res['valid_client_cnt']) +
               "Reported Rate PUB:%.0f SUB:%.0f and Reported Drop Percentage : %.4f" %
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
        pub_data = self.apps[self.zstpub]['stats'].values()[0]
        msg_cnt_pub_tx = pub_data['msg_cnt']
        bad_clients = 0
        client_rate = 0
        bad_client_rate = 0
        clients_packet_count = 0
        slow_clients_rate = 0
        slow_clients_packet_cnt = 0
        slow_clients_cnt = 0
        rec_clients_rate = 0
        rec_clients_packet_cnt = 0
        rec_clients_cnt = 0
        rec_cnt = 0

        stats = self.get_app_stats(self.zstsub)
        num_subs = len(stats)
        valid_client_cnt = 0
        for client in stats.keys():
            # l.info(" CLIENT = " + pformat(client) + " DATA = " + pformat(info))
            info = stats[client]
            task_id = info['task_id']
            slow_clients = self.get_app_property(self.zstsub, 'slow_clients')
            rec_clients = self.get_app_property(self.zstsub, 'reconnecting_clients')
            # we are seeing some of the clients compleately fail to receive
            # messages Need to create a seperate account for these clients.
            # For now will hack it to be grouped with slow clients.
            if (slow_clients and task_id in slow_clients) or info['msg_cnt'] == 0:
                slow_clients_rate += info['rate']
                slow_clients_packet_cnt += info['msg_cnt']
                slow_clients_cnt += 1
            elif rec_clients and task_id in rec_clients:
                rec_clients_rate += info['rate']
                rec_clients_packet_cnt += info['msg_cnt']
                rec_clients_cnt += 1
                rec_cnt += info['reconnect_cnt']
            else:
                client_rate += info['rate']
                clients_packet_count += info['msg_cnt']
                valid_client_cnt += 1
                if info['msg_cnt'] != msg_cnt_pub_tx:
                    if (bad_clients < 4):
                        l.info("[%s] Count Mismatch Info: %s" % (client, pformat(info)))
                    # else:
                    #    l.info("[%s] Count Mismatch Suppressing details (Use DCOS to get data)." % (client))
                    bad_clients += 1
                    bad_client_rate += info['rate']
        if bad_clients > 0:
            l.info("Total number of clients experiencing packet drop = %d out of %d clients" %
                   (bad_clients, num_subs))
            l.info('Average rate seen at the failing clients %f' % (bad_client_rate / bad_clients))
        else:
            l.info("No client experienced packet drops out of %d clients" % num_subs)
        l.info("Total packet's send by PUB:%d and average packets received by client:%d" %
               (msg_cnt_pub_tx, clients_packet_count / valid_client_cnt))
        l.info('Average rate seen at the pub %f and at clients %f' %
               (pub_data['rate'], (client_rate / valid_client_cnt)))
        if slow_clients_cnt:
            plos = ((msg_cnt_pub_tx - (1.0 * slow_clients_packet_cnt / slow_clients_cnt)) * 100.0 / msg_cnt_pub_tx)
            l.info("Slow Client[%d] :: Average Packets Received:%d and Average Rate: %f average packet loss %f" %
                   (slow_clients_cnt, slow_clients_packet_cnt / slow_clients_cnt,
                    slow_clients_rate / slow_clients_cnt, plos))
        if rec_clients_cnt:
            plos = ((msg_cnt_pub_tx - (1.0 * rec_clients_packet_cnt / rec_clients_cnt)) * 100.0 / msg_cnt_pub_tx)
            l.info("RECONNECTING Client"
                   "[%d] :: Average Packets Received:%d and Average Rate: %f"
                   " average packet loss %f Total Reconnects %d" %
                   (rec_clients_cnt, rec_clients_packet_cnt / rec_clients_cnt,
                    rec_clients_rate / rec_clients_cnt, plos, rec_cnt))

        result['client_count'] = num_subs
        result['packet_tx'] = msg_cnt_pub_tx
        result['average_packets'] = clients_packet_count / valid_client_cnt
        result['average_rate'] = client_rate / valid_client_cnt
        result['failing_clients'] = bad_clients
        result['average_tx_rate'] = pub_data['rate']
        result['valid_client_cnt'] = valid_client_cnt
        if bad_clients:
            result['failing_clients_rate'] = (bad_client_rate / bad_clients)
        result['average_packet_loss'] = \
            ((msg_cnt_pub_tx - (1.0 * clients_packet_count / valid_client_cnt)) * 100.0 / msg_cnt_pub_tx)
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

    def launch_zmq_pub(self):
        l.info("Launching the pub app")
        constraints = [self.app_constraints(field='hostname', operator='UNIQUE')]
        # Use cluster0 for launching the PUB
        if 0 in self.mesos_cluster:
            constraints.append(self.app_constraints(field=self.mesos_cluster[0]['cat'],
                                                    operator='CLUSTER', value=self.mesos_cluster[0]['match']))

        if not self.options.c_pub:
            self.create_hydra_app(name=self.zstpub, app_path='hydra.zmqtest.zmq_pub.run',
                                  app_args='%s %s %s %s' % (self.options.test_duration,
                                                            self.options.msg_batch,
                                                            self.options.msg_rate, self.options.total_sub_apps),
                                  cpus=0.01, mem=32,
                                  ports=[0],
                                  constraints=constraints)
        else:
            self.create_binary_app(name=self.zstpub,
                                   app_script='./src/main/scripts/zmq_pub',
                                   cpus=0.01, mem=32,
                                   ports=[0],
                                   constraints=constraints)

        # Find launched pub server's ip, rep PORT
        ipm = self.get_app_ipport_map(self.zstpub)
        assert(len(ipm) == 1)
        self.pub_ip = ipm.values()[0][1]
        self.pub_rep_taskport = str(ipm.values()[0][0])

        # self.pub_ip = self.find_ip_uniqueapp(self.zstpub)
        # tasks = self.get_app_tasks(self.zstpub)
        # assert(len(tasks) == 1)
        # assert(len(tasks[0].ports) == 1)
        # self.pub_rep_taskport = str(tasks[0].ports[0])
        l.info("[zmq_pub] ZMQ pub server running at [%s]", self.pub_ip)
        l.info("[zmq_pub] ZMQ REP server running at [%s:%s]", self.pub_ip, self.pub_rep_taskport)
        # Init ZMQPubAnalyser
        self.ha_pub = ZMQPubAnalyser(self.pub_ip, self.pub_rep_taskport, ipm.keys()[0])

    def launch_zmq_sub(self):
        l.info("Launching the sub app")
        constraints = []
        t_app_path = 'hydra.zmqtest.zmq_sub.run10'
        if self.options.c_sub:
            t_app_path = 'hydra.zmqtest.zmq_sub.run10cpp'

        # Use cluster 1 for launching the SUB
        if 1 in self.mesos_cluster:
            constraints.append(self.app_constraints(field=self.mesos_cluster[1]['cat'],
                                                    operator='CLUSTER', value=self.mesos_cluster[1]['match']))
        self.create_hydra_app(name=self.zstsub, app_path=t_app_path,
                              app_args='%s 15556' % (self.pub_ip),  # pub_ip, pub_port
                              cpus=0.01, mem=32,
                              ports=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                              constraints=constraints)

        # scale
        self.scale_sub_app()

    def scale_sub_app(self):
        self.scale_app(self.zstsub, self.options.total_sub_apps)
        self.remove_unresponsive_tasks(self.zstsub)

    def delete_all_launched_apps(self):
        l.info("Deleting all launched apps")
        l.info("Deleting PUB")
        self.delete_app(self.zstpub)
        l.info("Deleting SUBs")
        self.delete_app(self.zstsub)


class RunNegativeTest(object):
    def __init__(self, argv):
        raise Exception("Negative Test for Exception.")


class RunPositiveTest(object):
    def __init__(self, argv):
        pass


class RunTest(object):
    def __init__(self, argv):
        usage = ('python %prog --test_duration=<time to run test> --msg_batch=<msg burst batch before sleep>'
                 '--msg_rate=<rate in packet per secs> --total_sub_apps=<Total sub apps to launch>'
                 '--config_file=<path_to_config_file> --keep_running')
        parser = OptionParser(description='zmq scale test main',
                              version="0.1", usage=usage)
        parser.add_option("--test_duration", dest='test_duration', type='int', default=10)
        parser.add_option("--msg_batch", dest='msg_batch', type='int', default=100)
        parser.add_option("--msg_rate", dest='msg_rate', type='int', default=10000)
        parser.add_option("--total_sub_apps", dest='total_sub_apps', type='int', default=100)
        parser.add_option("--config_file", dest='config_file', type='string', default='hydra.ini')
        parser.add_option("--keep_running", dest='keep_running', action="store_true", default=False)
        parser.add_option("--c_pub", dest='c_pub', action="store_true", default=False)
        parser.add_option("--c_sub", dest='c_sub', action="store_true", default=False)
        parser.add_option("--slow_clients_percent", dest='slow_clients_percent', type='float', default=0)
        parser.add_option("--slow_clients_rate", dest='slow_clients_rate', type='int', default=1000)
        parser.add_option("--reconnecting_clients_percent", dest='rec_clients_percent', type='float', default=0)
        parser.add_option("--reconnecting_clients_rate", dest='rec_clients_rate', type='float', default=0.5)

        (options, args) = parser.parse_args()
        if ((len(args) != 0)):
            parser.print_help()
            sys.exit(1)
        r = RunTestZMQ(options, False)
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
