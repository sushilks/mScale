__author__ = 'AbdullahS'

from pprint import pprint, pformat  # NOQA
import logging
import websocket
import json
import time
from hydra.lib import util
from hydra.kraken.kraken_testbase import KrakenTestBase

l = util.createlogger('PGkrakenTestSuite', logging.INFO)
# l.setLevel(logging.DEBUG)


class PGKrakenTestSanity(KrakenTestBase):
    """
    PGKrakenTestSanity Class. Tests the following sanity:
    - Brings up PG DB on 3 slave nodes with a broker per slave node
    - Validates DHT ring is formed by quering DHT health via websocket
    - NEXT:
    - integrate launch of test clients and run sanity
    """
    class Factory():
        """
        Polymorphic factory to return Test Class.
        """
        def create(self, h_han):
            """
            Return PGKrakenTestSanity Class
            """
            l.info(h_han)
            return PGKrakenTestSanity(h_han)

    def __init__(self, h_han):
        """
        Initiate Test:
        @args:
        h_han:   hydra handle
        """
        super(PGKrakenTestSanity, self).__init__('PGKrakenTestSanity', h_han)
        self.run()

    def run(self):
        """
        run :)
        """
        self.prep_app_name()
        self.h_han.start_init()
        self.launch_db()
        self.assert_pg_broker_ring_green(self.ip_list)
        self.launch_test_client()

    def launch_broker(self, broker_idx, ip_list):
        """
        Launch PG broker
        @args:
        broker_idx:   Broker index e-g 0,1,2
        ip_list:      iplist of nodes expected to form a ring
        """
        app_name = self.broker_name_list[broker_idx]
        constraints = [self.h_han.app_constraints(field='hostname', operator='UNIQUE')]
        field = self.h_han.mesos_cluster[broker_idx]['cat']
        value = self.h_han.mesos_cluster[broker_idx]['match']
        l.info("launch_broker: broker[%s] ip_list [%s] APP constraints [field=%s, value=%s]", app_name,
               ip_list, field, value)
        constraints.append(self.h_han.app_constraints(field=field,
                                                      operator='CLUSTER', value=value))
        self.h_han.create_binary_app(name=app_name,
                                     app_script='./src/main/python/hydra/kraken/plumgrid/launch_pg_db.sh %s' % ip_list,
                                     cpus=1, mem=4096,
                                     ports=[0],
                                     constraints=constraints)

    def launch_test_client(self):
        """
        Launch PG broker
        @args:
        broker_idx:   Broker index e-g 0,1,2
        ip_list:      iplist of nodes expected to form a ring
        """
        field = "group"
        value = "node-0"
        constraints = []
        constraints.append(self.h_han.app_constraints(field=field, operator='CLUSTER', value=value))
        self.h_han.create_binary_app(name=self.test_name,
                                     app_script='./src/main/python/hydra/kraken/plumgrid/launch_test_client.sh',
                                     cpus=0.1, mem=256,
                                     ports=[0],
                                     constraints=constraints)
        self.h_han.scale_and_verify_app(self.test_name, 10)

    def launch_db(self):
        """
        Launch PG DB
        """
        l.info(self.h_han.mesos_cluster)
        ip_list_str = self.prep_iplist_with_attr()
        for x in range(self.broker_nodes):
            self.launch_broker(x, ip_list_str)

    def prep_app_name(self):
        """
        prep current app names to be launched via hydra on mesos cluster
        Names are added to hydra layer via self.h_han.add_appid (hydra.lib.runtestbase)
        for auto-deletion, pre check for existing apps etc
        """
        self.broker_name_list = []
        self.broker_nodes = 3
        self.test_name = "broker-client"
        for x in range(self.broker_nodes):
            app_name = "broker" + "-%d" % x
            self.h_han.add_appid(app_name)
            self.broker_name_list.append(app_name)
        self.h_han.add_appid(self.test_name)

    def check_pg_broker_node_health(self, ip):
        """
        Function to check pg dht node health
        Does a websocket query
        @args:
        ip:     IP to query
        """
        ws_port = "12359"
        ws_ip_port = ip + ":%s" % ws_port
        ws = websocket.create_connection("ws://" + ws_ip_port)
        ws.send("/health")
        rep = ws.recv()
        ws.close()
        rep = json.loads(rep)
        return rep["service_health"]

    def assert_pg_broker_ring_green(self, ip_list, timeout=20):
        """
        Function to check pg broker ring  health
        asserts if any node is degraded
        @args:
        ip_list:        list of ips to query for health
        timeout:        Timeout
        """
        fail = False
        start_time = time.time()
        while (time.time() - start_time < timeout):
            fail = False
            for ip in ip_list:
                res = self.check_pg_broker_node_health(ip)
                if not res:
                    l.info("Unable to get pg dht node health status")
                    fail = True
                    continue
                l.info("%s: %s" % (ip, res))
                if (res == "GREEN"):
                    continue
                # everything that is not green is a failure
                fail = True
            time.sleep(1)
            if not fail:
                return True
        assert(fail is False)
