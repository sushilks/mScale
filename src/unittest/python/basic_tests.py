__author__ = 'sushil'
import sys
from sys import path
path.append("src/main/python")

# from mockito import mock, verify
import unittest
import numbers
import requests
import time
import os
import zmq

from pprint import pprint
from hydra.lib.runtestbase import RunTestBase

'''
tests :
 -Check connectivity to mesos
 -check connectivity to marathon
 -check number of slaves
 - check cpu/memory etc. on slave
 - check app server deployment
 - chack launching of app-s
 - check communication to app-s
 - check destroy of app-s
 - check launch of client app-c
 - check communication between  app-s, app-c
 check scale up/down of app-s
 check cli outputs
'''



# def setUpModule():  # NOQA
#    # gets called only once per run
#    print("SETUPMODULE CALLED")


# def teadDownModule():  # NOQA
#    # gets called only once per run
#    print("TearDown Module Called")

def send_zmq_message(this, sock, message, expectedVal=None):
    # pprint('sending message:' + message)
    sock.send(message)
    m = sock.recv()
    # pprint('\tgot response :' + m)
    if expectedVal != None:
        this.assertEqual(m, expectedVal)
    return m



class mScaleUnitTest(unittest.TestCase):  # NOQA
    @classmethod
    def setUpClass(cls):
        # Gets called only once per class invocation
        print("SETUP CLASS CALLED")
        #rt = cls()
        #cls._rt = .init('basicTest', 'hydra.ini')
        cls.runtest = RunTestBase('basicTest', config_filename='hydra.ini',
                                  startappserver=False)
        #return rt

    @classmethod
    def tearDownClass(cls):
        # get's called only once per class invocation
        #print("TearDown Class Called")
        cls.runtest.stop_appserver()
        del cls.runtest
        cls.runtest = None

    def setUp(self):
        # get's called per test
        #print ("SETUP Called")
        self.rt = self.__class__.runtest
        self.rt.init_mesos()
        self.rt.init_marathon()
        self.rt.init_appserver_dir()
        self.rt.start_appserver()


    def tearDown(self):
        # gets called per test
        # print("TearDown Caleldd")
        self.rt = None

    def test_mesos_health(self):
        #slaveCount = self.rt.mesos.get_slave_cnt()
        #self.assertTrue(slaveCount > 0)
        self.assertTrue(self.rt.get_mesos_health(), "Unable to get health status from mesos")
        ver = self.rt.get_mesos_version()
        self.assertNotEqual(ver, None, "Unable to get version information from mesos")
        self.assertTrue(len(ver['version']) > 0, "Unable to get a valid version for mesos")

    def test_mesos_version(self):
        ver = self.rt.get_mesos_version()
        self.assertNotEqual(ver, None, "Unable to get version information from mesos")
        self.assertTrue(len(ver['version']) > 0, "Unable to get a valid version for mesos")

    def test_mesos_stats(self):
        stats = self.rt.get_mesos_stats()
        self.assertNotEqual(stats, None, "Unable to get stats information from mesos")
        self.assertTrue(isinstance(stats['cpus_total'], numbers.Number))
        self.assertTrue(isinstance(stats['mem_total_bytes'], numbers.Number))
        self.assertTrue(isinstance(stats['mem_free_bytes'], numbers.Number))
        self.assertTrue(stats['cpus_total'] > 0)
        self.assertTrue(stats['mem_total_bytes'] > 0)
        self.assertTrue(stats['mem_free_bytes'] > 0)


    def test_mesos_slaves(self):
        slaveCount = self.rt.get_mesos_slave_count()
        self.assertTrue(slaveCount > 0, 'No slaves detected on mesos cluster')

    def test_marathon_connectivity(self):
        a = self.rt.ping()
        self.assertEqual(a, 'pong\n')

    def test_app_server_start(self):
        #populate the live directory
        #self.rt.init_appserver_dir()
        #start the app server
        #self.rt.start_appserver()
        # do a get from app server
        for idx in range(0, 2):
            try:
                r = requests.get('http://127.0.0.1:' + str(self.rt.myport) + '/')
                break
            except:
                # try for 2 seconds to get the connection
                pass
            time.sleep(1)
        r = requests.get('http://127.0.0.1:' + str(self.rt.myport) + '/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.find('basicTest.tgz') >= 0)

    def test_app_launch(self):
        tapp = 'testapp1'
        # clean up any previous app by this name
        self.rt.delete_app(tapp)
        self.rt.create_hydra_app(name=tapp, app_path='hydra.selftest.agents.Test',
                                 app_args='5599 5598 0',
                                 cpus=0.01, mem=32)
        taskip = self.rt.find_ip_uniqueapp(tapp)
        pprint('task is launched at ip=' + taskip)
        # stop and clean up
        self.rt.delete_app(tapp)
        self.assertTrue(len(taskip) >= 7)
        a = self.rt.get_app(tapp)
        self.assertTrue(a == None)

    def test_app_communication(self):
        tapp = 'testapp2'
        # clean up any previous app by this name
        self.rt.delete_app(tapp)
        self.rt.create_hydra_app(name=tapp, app_path='hydra.selftest.agents.Test',
                                 app_args='5599 5598 0',
                                 cpus=0.01, mem=32)
        taskip = self.rt.find_ip_uniqueapp(tapp)
        pprint('task is launched at ip=' + taskip)
        # now send a message to this app to find out how it's doing
        zctx = zmq.Context()
        zsocket = zctx.socket(zmq.REQ)
        zsocket.connect("tcp://%s:5599" % taskip)
        zsocket.send('ping');
        message = zsocket.recv()

        # stop and clean up
        self.rt.delete_app(tapp)
        self.assertEqual(message, 'pong')


    def test_multiple_apps(self):
        tapp_cli0 = 'testapp.c0'
        tapp_cli1 = 'testapp.c1'
        tapp_cli2 = 'testapp.c2'
        tapp_srv = 'testapp.s'
        # clean up any previous app by this name
        self.rt.delete_app(tapp_cli0)
        self.rt.delete_app(tapp_cli1)
        self.rt.delete_app(tapp_cli2)
        self.rt.delete_app(tapp_srv)
        self.rt.create_hydra_app(name=tapp_srv, app_path='hydra.selftest.agents.Test',
                                 app_args='5599 5598 0',
                                 cpus=0.01, mem=32)
        srvip = self.rt.find_ip_uniqueapp(tapp_srv)

        self.rt.create_hydra_app(name=tapp_cli0, app_path='hydra.selftest.agents.Test',
                                 app_args='5597 0 %s:5598' % srvip,
                                 cpus=0.01, mem=32)
        cliip0 = self.rt.find_ip_uniqueapp(tapp_cli0)

        pprint('task is launched at srvip=' + srvip + ' cliip0=' + cliip0)
        # now send a message to this app to find out how it's doing
        zctx = zmq.Context()
        clisocket0 = zctx.socket(zmq.REQ)
        srvsocket = zctx.socket(zmq.REQ)
        clisocket0.connect("tcp://%s:5597" % cliip0)
        srvsocket.connect("tcp://%s:5599" % srvip)
        # check if we can talk to both client and server programs
        send_zmq_message(self, clisocket0, 'ping', 'pong')
        send_zmq_message(self, srvsocket, 'ping', 'pong')
        send_zmq_message(self, srvsocket, 'disable_pub', 'ok')
        send_zmq_message(self, srvsocket, 'reset_pub', 'ok')
        send_zmq_message(self, clisocket0, 'reset_sub', 'ok')
        send_zmq_message(self, srvsocket, 'delay:0.01', 'ok')
        send_zmq_message(self, srvsocket, 'enable_pub', 'ok')
        time.sleep(1)
        send_zmq_message(self, srvsocket, 'disable_pub', 'ok')
        srv_cnt = send_zmq_message(self, srvsocket, 'cnt_pub')
        cli_cnt = send_zmq_message(self, clisocket0, 'cnt_sub')
        pprint("Srv_cnt = " + str(srv_cnt))
        pprint("cli_cnt = " + str(cli_cnt))
        self.assertEqual(srv_cnt, cli_cnt)
        send_zmq_message(self, srvsocket, 'reset_pub', 'ok')
        # launch 2 more clients
        self.rt.create_hydra_app(name=tapp_cli1, app_path='hydra.selftest.agents.Test',
                                 app_args='5596 0 %s:5598' % srvip,
                                 cpus=0.01, mem=32)
        cliip1 = self.rt.find_ip_uniqueapp(tapp_cli1)
        self.rt.create_hydra_app(name=tapp_cli2, app_path='hydra.selftest.agents.Test',
                                 app_args='5595 0 %s:5598' % srvip,
                                 cpus=0.01, mem=32)
        cliip2 = self.rt.find_ip_uniqueapp(tapp_cli2)
        clisocket1 = zctx.socket(zmq.REQ)
        clisocket2 = zctx.socket(zmq.REQ)
        clisocket1.connect("tcp://%s:5596" % cliip1)
        clisocket2.connect("tcp://%s:5595" % cliip2)
        send_zmq_message(self, clisocket1, 'ping', 'pong')
        send_zmq_message(self, clisocket2, 'ping', 'pong')
        send_zmq_message(self, clisocket0, 'reset_sub', 'ok')
        send_zmq_message(self, clisocket1, 'reset_sub', 'ok')
        send_zmq_message(self, clisocket2, 'reset_sub', 'ok')
        send_zmq_message(self, srvsocket, 'enable_pub', 'ok')
        time.sleep(1)
        send_zmq_message(self, srvsocket, 'disable_pub', 'ok')
        srv_cnt = send_zmq_message(self, srvsocket, 'cnt_pub')
        cli_cnt0 = send_zmq_message(self, clisocket0, 'cnt_sub')
        cli_cnt1 = send_zmq_message(self, clisocket1, 'cnt_sub')
        cli_cnt2 = send_zmq_message(self, clisocket2, 'cnt_sub')

        pprint(' cli_cnt0  =  ' + str(cli_cnt0))
        pprint(' cli_cnt1  =  ' + str(cli_cnt1))
        pprint(' cli_cnt2  =  ' + str(cli_cnt2))

        # stop and clean up
        self.rt.delete_app(tapp_srv)
        self.rt.delete_app(tapp_cli0)
        self.rt.delete_app(tapp_cli1)
        self.rt.delete_app(tapp_cli2)

        self.assertEqual(srv_cnt, cli_cnt0)
        self.assertEqual(srv_cnt, cli_cnt1)
        self.assertEqual(srv_cnt, cli_cnt2)


if __name__ == '__main__':
    unittest.main()

