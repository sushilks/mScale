__author__ = 'sushil'
from sys import path
path.append("src/main/python")

# from mockito import mock, verify
import unittest
import numbers
import requests
import time
import zmq

from pprint import pprint
from hydra.lib.hydrabase import HydraBase

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
- check scale up of app-s
 check scale down of app-s
 check cli outputs
'''
# def setUpModule():  # NOQA
#    # gets called only once per run
#    print("SETUPMODULE CALLED")

# def teadDownModule():  # NOQA
#    # gets called only once per run
#    print("TearDown Module Called")


def send_zmq_message(this, sock, message, expected_val=None):
    # pprint('sending message:' + message)
    sock.send_string(message)
    m = sock.recv().decode("utf-8")
    # pprint('\tgot response :' + m)
    if expected_val:
        this.assertEqual(m, expected_val)
    return m


class hydraUnitTest(unittest.TestCase):  # NOQA
    @classmethod
    def setUpClass(cls):
        # Gets called only once per class invocation
        # print("SETUP CLASS CALLED")
        # rt = cls()
        # cls._rt = .init('basicTest', 'hydra.ini')
        cls.runtest = HydraBase('basicTest', None, None,
                                startappserver=False)
        # return rt

    @classmethod
    def tearDownClass(cls):
        # get's called only once per class invocation
        # print("TearDown Class Called")
        cls.runtest.stop_appserver()
        del cls.runtest
        cls.runtest = None

    def setUp(self):
        # get's called per test
        # print ("SETUP Called")
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
        # slaveCount = self.rt.mesos.get_slave_cnt()
        # self.assertTrue(slaveCount > 0)
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
        slave_count = self.rt.get_mesos_slave_count()
        self.assertTrue(slave_count > 0, 'No slaves detected on mesos cluster')

    def test_marathon_connectivity(self):
        a = self.rt.ping()
        self.assertEqual(a, 'pong\n')

    def test_app_server_start(self):
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
        self.assertTrue(r.content.decode("utf-8").find('basicTest.tgz') >= 0)

    def test_app_launch(self):
        tapp = 'testapp1'
        # clean up any previous app by this name
        self.rt.delete_app(tapp)
        self.rt.create_hydra_app(name=tapp, app_path='hydra.selftest.agents.Test',
                                 app_args='5598 0',
                                 ports=[0],
                                 cpus=0.01, mem=32)
        taskip = self.rt.find_ip_uniqueapp(tapp)
        tasks = self.rt.get_app_tasks(tapp)
        self.assertTrue(len(tasks) == 1)
        self.assertTrue(len(tasks[0].ports) == 1)
        taskport = str(tasks[0].ports[0])
        pprint('task is launched at ip=' + taskip + ":" + taskport)
        # stop and clean up
        self.rt.delete_app(tapp)
        self.assertTrue(len(taskip) >= 7)
        a = self.rt.get_app(tapp)
        self.assertTrue(not a)

    def test_app_communication(self):
        tapp = 'testapp2'
        # clean up any previous app by this name
        self.rt.delete_app(tapp)
        self.rt.create_hydra_app(name=tapp, app_path='hydra.selftest.agents.Test',
                                 app_args='5598 0',
                                 cpus=0.01, mem=32)
        taskip = self.rt.find_ip_uniqueapp(tapp)
        tasks = self.rt.get_app_tasks(tapp)
        self.assertTrue(len(tasks) == 1)
        self.assertTrue(len(tasks[0].ports) == 1)
        taskport = str(tasks[0].ports[0])

        pprint('task is launched at ip=' + taskip + ":" + taskport)
        # now send a message to this app to find out how it's doing
        zctx = zmq.Context()
        zsocket = zctx.socket(zmq.REQ)
        zsocket.connect("tcp://%s:%s" % (taskip, taskport))
        zsocket.send_string('ping')
        message = zsocket.recv().decode("utf-8")

        # stop and clean up
        self.rt.delete_app(tapp)
        self.assertEqual(message, 'pong')
'''
    TODO: Enable this test case.
    def test_multiple_apps(self):
        tapp_cli0 = 'testapp.c0'
        tapp_srv = 'testapp.s'
        # clean up any previous app by this name
        self.rt.delete_app(tapp_cli0)
        self.rt.delete_app(tapp_srv)
        self.rt.create_hydra_app(name=tapp_srv, app_path='hydra.selftest.agents.Test',
                                 app_args='5598 0',
                                 ports=[0],
                                 cpus=0.01, mem=32)
        srvip = self.rt.find_ip_uniqueapp(tapp_srv)
        tasks = self.rt.get_app_tasks(tapp_srv)
        self.assertTrue(len(tasks) == 1)
        self.assertTrue(len(tasks[0].ports) == 1)
        taskport = str(tasks[0].ports[0])
        srvipport = srvip + ':' + taskport

        self.rt.create_hydra_app(name=tapp_cli0, app_path='hydra.selftest.agents.Test',
                                 ports=[0],
                                 app_args='0 %s:5598' % srvip,
                                 cpus=0.01, mem=32)
        cliip0 = self.rt.find_ip_uniqueapp(tapp_cli0)
        tasks = self.rt.get_app_tasks(tapp_cli0)
        self.assertTrue(len(tasks) == 1)
        self.assertTrue(len(tasks[0].ports) == 1)
        taskport = str(tasks[0].ports[0])
        cliip0 += ':' + taskport

        pprint('task is launched at srvip=' + srvipport + ' cliip0=' + cliip0)
        # now send a message to this app to find out how it's doing
        zctx = zmq.Context()
        clisocket0 = zctx.socket(zmq.REQ)
        srvsocket = zctx.socket(zmq.REQ)
        clisocket0.connect("tcp://%s" % cliip0)
        srvsocket.connect("tcp://%s" % srvipport)
        # check if we can talk to both client and server programs
        send_zmq_message(self, clisocket0, 'ping', 'pong')
        send_zmq_message(self, srvsocket, 'ping', 'pong')
        # find out what port is reported by the marathon
        tasks0 = self.rt.get_app_tasks(tapp_cli0)
        for task in tasks0:
            print(" PORTS reported by api taskid[" + task.id + " PORT = " + pformat(task.ports))
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

        self.rt.__mt.scale_app(tapp_cli0, 10)
        self.rt.__mt.wait_app_ready(tapp_cli0, 10)
        cliiplist = []
        tasks0 = self.rt.get_app_tasks(tapp_cli0)
        for task in tasks0:
            taskip = self.rt.get_ip_hostname(task.host)
            print(" PORTS reported by api taskid[" + task.id + " IP_PORT = " + taskip + ":" + pformat(task.ports[0]))
            cliiplist.append(taskip + ':' + str(task.ports[0]))
        # launch 2 more clients
        clisockets = []
        for ipp in cliiplist:
            sock = zctx.socket(zmq.REQ)
            sock.connect("tcp://%s" % ipp)
            clisockets.append(sock)
        for cli in clisockets:
            send_zmq_message(self, cli, 'ping', 'pong')
            send_zmq_message(self, cli, 'reset_sub', 'ok')
        send_zmq_message(self, srvsocket, 'enable_pub', 'ok')
        time.sleep(1)
        send_zmq_message(self, srvsocket, 'disable_pub', 'ok')
        srv_cnt = send_zmq_message(self, srvsocket, 'cnt_pub')
        cli_cnt = []
        for cli in clisockets:
            cli_cnt.append(send_zmq_message(self, cli, 'cnt_sub'))
        for idx in range(0, len(cli_cnt)):
            pprint(' cli_cnt%d  =  %s' % (idx, cli_cnt[idx]))
        # stop and clean up
        self.rt.delete_app(tapp_srv)
        self.rt.delete_app(tapp_cli0)
        for idx in range(0, len(cli_cnt)):
            self.assertEqual(srv_cnt, cli_cnt[idx])
'''
if __name__ == '__main__':
    unittest.main()
