__author__ = 'sushil, abdullahS'

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


class RunTest(RunTestBase):
    def __init__(self, argv):
        usage = ('python %prog --total_msgs=<total msgs to send> --msg_batch=<msg burst batch before sleep>'
                 '--msg_delay=<msg delay in secs> --total_sub_apps=<Total sub apps to launch>'
                 '--config_file=<path_to_config_file>')
        parser = OptionParser(description='zmq scale test master',
                              version="0.1", usage=usage)
        parser.add_option("--total_msgs", dest='total_msgs', type='int', default=10000)
        parser.add_option("--msg_batch", dest='msg_batch', type='int', default=100)
        parser.add_option("--msg_delay", dest='msg_delay', type='float', default=0.01)
        parser.add_option("--total_sub_apps", dest='total_sub_apps', type='int', default=100)
        parser.add_option("--config_file", dest='config_file', type='string', default='hydra.ini')

        (options, args) = parser.parse_args()
        if ((len(args) != 0)):
            parser.print_help()
            sys.exit(1)
        self.total_msgs = options.total_msgs
        self.msg_batch = options.msg_batch
        self.msg_delay = options.msg_delay
        self.total_sub_apps = options.total_sub_apps
        self.config_file = options.config_file

        config = ConfigParser()
        config_fn = self.config_file
        RunTestBase.__init__(self, 'zmqScale', config, config_fn)
        self.zstpub = '/zst-pub'
        self.zstsub = '/zst-sub'
        self.add_appid(self.zstpub)
        self.add_appid(self.zstsub)
        self.start_init()
        self.run_test()
        self.stop_appserver()

    def run_test(self):
        # Launch zmq pub
        self.launch_zmq_pub()

        # Launch zmq sub up to self.total_sub_apps
        self.launch_zmq_sub()

        # Signal PUB to start sending all messages, blocks until PUB notifies
        self.signal_pub_send_msgs()

        #  Fetch all client SUB data
        self.fetch_all_sub_clients_data()

        #  Delete all launched apps
        self.delete_all_launched_apps()
        l.info("Successfully finished gathering all data")

        l.info("================================================")
        bad_clients = 0
        for client, info in self.all_sub_clients_info.items():
            if info.values()[0] < self.total_msgs:
                l.info("Client: %s", client)
                l.info("Info: %s", info)
                bad_clients += 1
        if bad_clients > 0:
            l.info("Total number of clients experiencing packet drop = %d", bad_clients)
        else:
            l.info("OK")

    def launch_zmq_pub(self):
        l.info("Launching the pub app")
        self.create_hydra_app(name=self.zstpub, app_path='hydra.zmqtest.zmq_pub.run',
                              app_args='%s %s %s %s' % (self.total_msgs,
                                                        self.msg_batch,
                                                        self.msg_delay, self.total_sub_apps),
                              cpus=0.01, mem=32,
                              ports=[0],
                              constraints=[self.app_constraints(field='hostname', operator='UNIQUE')])
        self.wait_app_ready(self.zstpub, 1)
        # Find launched pub server's ip, rep PORT
        self.pub_ip = self.find_ip_uniqueapp(self.zstpub)
        tasks = self.get_app_tasks(self.zstpub)
        assert(len(tasks) == 1)
        assert(len(tasks[0].ports) == 1)
        self.pub_rep_taskport = str(tasks[0].ports[0])
        l.info("[zmq_pub] ZMQ pub server running at [%s]", self.pub_ip)
        l.info("[zmq_pub] ZMQ REP server running at [%s:%s]", self.pub_ip, self.pub_rep_taskport)

    def launch_zmq_sub(self):
        l.info("Launching the sub app")
        self.create_hydra_app(name=self.zstsub, app_path='hydra.zmqtest.zmq_sub.run',
                              app_args='%s 15556' % (self.pub_ip),  # pub_ip, pub_port
                              cpus=0.01, mem=32,
                              ports=[0])
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
            assert(len(task.ports) == 1)
            sub_app_ip = self.get_ip_hostname(task.host)
            sub_app_rep_port = task.ports[0]
            self.sub_app_ip_rep_port_map[task.id] = {sub_app_rep_port: sub_app_ip}
        # l.info(self.sub_app_ip_rep_port_map)

    def signal_pub_send_msgs(self):
        l.info("Sending signal to PUB to start sending all messages..")
        pub_rep_kwargs = {}
        pub_rep_kwargs.update({"server_ip": self.pub_ip})
        pub_rep_kwargs.update({"server_port": self.pub_rep_taskport})
        ha_pub = HAnalyser(self.pub_ip, self.pub_rep_taskport)
        # Signal it to start sending data, blocks until PUB responsds with "DONE" after sending all data
        ha_pub.do_req("start")

    def fetch_all_sub_clients_data(self):
        l.info("Attempting to fetch all client data..")
        # TODO: (AbdullahS): Add more stuff, timestamp, client ip etc
        self.all_sub_clients_info = {}  # stores a mapping of client_id: {msg_count: x}
        for task_id, info in self.sub_app_ip_rep_port_map.items():
            l.info(task_id)
            l.info(info)
            port = info.keys()[0]
            ip = info.values()[0]
            ha_sub = HAnalyser(ip, port)
            # Signal it to start sending data, blocks until PUB responsds with "DONE" after sending all data
            ha_sub.do_req_update_data("stats_req")
            ha_sub.stop()  # closes the ANalyser socket, can not be used anymore
            self.all_sub_clients_info.update(ha_sub.get_data())

    def delete_all_launched_apps(self):
        l.info("Deleting all launched apps")
        l.info("Deleting PUB")
        self.delete_app(self.zstpub)
        l.info("Deleting SUBs")
        self.delete_app(self.zstsub)
