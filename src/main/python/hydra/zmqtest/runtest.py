__author__ = 'sushil, abdullahS'

import sys
from pprint import pprint, pformat  # NOQA
from marathon.models import MarathonApp, MarathonConstraint
import time
import logging
from hydra.lib import util
from hydra.lib.h_analyser import HAnalyser
from hydra.lib.runtestbase import RunTestBase
from hydra.zmqtest import zmq_config
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
        config = ConfigParser()
        config_fn = 'hydra.ini'
        if len(argv) >= 2:
            config_fn = argv[1]
            del argv[1]
        RunTestBase.__init__(self, 'zmqScale', config, config_fn)
        self.zstpub = '/zst-pub'
        self.zstsub = '/zst-sub'
        self.add_appid(self.zstpub)
        self.add_appid(self.zstsub)
        #self.total_sub_apps = 200
        self.total_sub_apps = zmq_config.total_apps
        self.start_init()
        self.run_test()

    def run_test(self):
        # Launch zmq pub
        self.launch_zmq_pub()

        # Launch zmq sub up to self.total_sub_apps
        self.launch_zmq_sub()

        # Signal PUB to start sending all messages, blocks until PUB notifies
        l.info("Waiting for 10 secs before signalling PUB to send messages ..")
        time.sleep(10)
        self.signal_pub_send_msgs()

        #  Fetch all client SUB data
        self.fetch_all_sub_clients_data()

        #  Delete all launched apps
        self.delete_all_launched_apps()
        l.info("Successfully finished gathering all data")

        l.info("================================================")
        for client, info in self.all_sub_clients_info.items():
            l.info("Client: %s", client)
            l.info("Info: %s", info)
        l.info("================================================")
        l.info("Please press ctrl+z  and then \"kill %1\"  twice.. sorry, will figure this out soon")
        return

    def launch_zmq_pub(self):
        l.info("Launching the pub app")
        self.create_hydra_app(name=self.zstpub, app_path='hydra.zmqtest.zmq_pub.run',
                              app_args='0.0001', # msg delay, msg count
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
        time.sleep(2)

    def launch_zmq_sub(self):
        l.info("Launching the sub app")
        self.create_hydra_app(name=self.zstsub, app_path='hydra.zmqtest.zmq_sub.run',
                              app_args='%s 15556' % (self.pub_ip), # pub_ip, pub_port
                              cpus=0.01, mem=32,
                              ports=[0])
        self.wait_app_ready(self.zstsub, 1)

        # scale
        l.info("Scaling sub app to [%d]", self.total_sub_apps)
        self.scale_app(self.zstsub, self.total_sub_apps)
        self.wait_app_ready(self.zstsub, self.total_sub_apps)

        # Extract ip, rep server port for data querying
        self.sub_app_ip_rep_port_map = {} # key = port, value=ip
        tasks = self.get_app_tasks(self.zstsub)
        assert(len(tasks) == self.total_sub_apps)
        for task in tasks:
            assert(len(task.ports) == 1)
            sub_app_ip = self.get_ip_hostname(task.host)
            sub_app_rep_port = task.ports[0]
            self.sub_app_ip_rep_port_map.update({sub_app_rep_port: sub_app_ip})


    def signal_pub_send_msgs(self):
        l.info("Sending signal to PUB to start sending all messages..")
        pub_rep_kwargs = {}
        pub_rep_kwargs.update({"server_ip": self.pub_ip})
        pub_rep_kwargs.update({"server_port": self.pub_rep_taskport})
        ha_pub = HAnalyser(**pub_rep_kwargs)
        time.sleep(2)
        # Signal it to start sending data, blocks until PUB responsds with "DONE" after sending all data
        ha_pub.do_req("start")


    def fetch_all_sub_clients_data(self):
        l.info("Attempting to fetch all client data..")
        # TODO: (AbdullahS): Add more stuff, timestamp, client ip etc
        self.all_sub_clients_info = {} # stores a mapping of client_id: {msg_count: x}
        for port, ip in self.sub_app_ip_rep_port_map.items():
            sub_rep_kwargs = {}
            sub_rep_kwargs.update({"server_ip": ip})
            sub_rep_kwargs.update({"server_port": port})
            ha_sub= HAnalyser(**sub_rep_kwargs)
            # Signal it to start sending data, blocks until PUB responsds with "DONE" after sending all data
            ha_sub.do_req_update_data("stats_req")
            self.all_sub_clients_info.update(ha_sub.get_data())

    def delete_all_launched_apps(self):
        l.info("Deleting all launched apps")
        l.info("Deleting PUB")
        self.delete_app(self.zstpub)
        l.info("Deleting SUBs")
        self.delete_app(self.zstsub)
