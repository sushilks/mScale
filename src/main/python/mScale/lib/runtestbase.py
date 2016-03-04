__author__ = 'sushil'

import netifaces
import logging
import os
import time
import sys
from mScale.lib import appserver, mmapi, util

l = util.createlogger('runTestBase', logging.INFO)
# l.setLevel(logging.DEBUG)


class RunTestBase(object):
    def __init__(self, test_name, config):
        self.testName = test_name
        self.myport = config.getint('zst', 'port')
        self.myserver = appserver.TServer(self.myport, 'live')
        self.myserver.start()
        self.mydev = config.get('zst', 'dev')
        self.myip = netifaces.ifaddresses(self.mydev)[2][0]['addr']
        self.myaddr = 'http://' + self.myip + ':' + str(self.myport)

        # now init the marathon plugin and create a app for this path
        self.mesos_addr = 'http://' + config.get('mesos', 'ip') + ':' + \
                          config.get('mesos', 'port')
        self.marathon_addr = 'http://' + config.get('marathon', 'ip') + ':' + \
                             config.get('marathon', 'port')
        self.appIdList = []
        self.mesos = None
        self.mt = None
        self.appItemToUpload = ['target', 'src']

    def add_appid(self, name):
        self.appIdList.append(name)

    def add_appitem_toupload(self, item):
        self.appItemToUpload.append(item)

    def start_init(self):
        l.info("Creating Mesos Client")
        self.mesos = mmapi.MesosIF(self.mesos_addr)
        l.info("Creating Marathon Client")
        self.mt = mmapi.MarathonIF(self.marathon_addr, self.myip, self.mesos)
        l.info("Delete any pre-existing apps")
        for app in self.appIdList:
            self.mt.delete_app_ifexisting(app)
        l.info("Waiting for delete to complete")
        for app in self.appIdList:
            self.mt.wait_app_removal(app)
        l.info("Populating the app on the server")
        os.system("rm -f ../live/" + self.testName + ".tgz")
        os.system("cd .. && tar cfz live/" + self.testName + ".tgz " + " ".join(self.appItemToUpload))

    def get_appserver_addr(self):
        return self.myaddr

    def get_app_uri(self):
        return self.get_appserver_addr() + '/' + self.testName + '.tgz'

    def find_ip_uniqueapp(self, app):
        a1 = self.mt.wait_app_ready(app, 1)
        for task in a1.tasks:
            l.info("TASK " + task.id + " Running on host : " + task.host + ' IP = ' +
                   self.mesos.get_slave_ip_from_hn(task.host))
            return self.mesos.get_slave_ip_from_hn(task.host)
        l.warn("Unable to find IP address for app " + app)
        return None

    def get_cmd(self, function_path, arguments):
        return 'cd ./src/main/scripts && ./mscale ' + \
               function_path + ' ' + arguments

    def wait_for_interrupt(self):
        try:
            while 1:
                sys.stdout.flush()
                time.sleep(1)
        except KeyboardInterrupt:
            l.info("Exiting")
            self.myserver.stop()
            self.myserver.join()
