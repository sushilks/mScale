__author__ = 'sushil'

import netifaces
import logging
import os
import time
import sys
import code
import traceback
import signal
from pprint import pprint, pformat  # NOQA
from hydra.lib import appserver, mmapi, util
try:
    # Python 2.x
    from ConfigParser import ConfigParser
except ImportError:
    # Python 3.x
    from configparser import ConfigParser

l = util.createlogger('runTestBase', logging.INFO)
from marathon.models import MarathonApp, MarathonConstraint
# l.setLevel(logging.DEBUG)


def debug(sig, frame):
    """Interrupt running process, and provide a python prompt for
    interactive debugging."""
    d = {'_frame': frame}         # Allow access to frame object.
    d.update(frame.f_globals)  # Unless shadowed by global
    d.update(frame.f_locals)

    i = code.InteractiveConsole(d)
    message = "Signal received : entering python shell.\nTraceback:\n"
    message += ''.join(traceback.format_stack(frame))
    i.interact(message)


class RunTestBase(object):
    def __init__(self, test_name, config=None, config_filename=None,
                 startappserver=True):
        if not config:
            config = ConfigParser()
        if config_filename:
            if not os.path.isfile(config_filename):
                l.error("Unable to open config file %s" % config_filename)
                raise Exception("Unable to open config file %s" % config_filename)
            config.read(config_filename)
        self.pwd = os.getcwd()
        self.testName = test_name
        self.appserver_running = False
        self.myport = config.getint('hydra', 'port')
        self.mydev = config.get('hydra', 'dev')
        self.myip = netifaces.ifaddresses(self.mydev)[2][0]['addr']
        self.myaddr = 'http://' + self.myip + ':' + str(self.myport)

        signal.signal(signal.SIGUSR1, debug)

        # extract cluster information
        self.mesos_cluster = {}
        for idx in range(0, 10):
            cn = 'cluster' + str(idx)
            if self.config.has_option('mesos', cn):
                dt = self.config.get('mesos', cn).split('.')
                self.mesos_cluster[idx] = {'cat': dt[0], 'match': '.'.join(dt[1:])}

        # now init the marathon plugin and create a app for this path
        self.mesos_addr = 'http://' + config.get('mesos', 'ip') + ':' + \
                          config.get('mesos', 'port')
        self.marathon_addr = 'http://' + config.get('marathon', 'ip') + ':' + \
                             config.get('marathon', 'port')
        self.appIdList = []
        self.__mesos = None
        self.__mt = None
        self.appItemToUpload = ['target', 'src']
        self.appserver_init_done = False
        if startappserver:
            self.start_appserver()

    def start_appserver(self):
        if not self.appserver_running:
            self.myserver = appserver.TServer(self.myport, self.pwd + '/live')
            self.myserver.start()
            self.appserver_running = True
        self.init_appserver_dir()

    def stop_appserver(self):
        self.myserver.stop()
        self.myserver.join()
        self.appserver_running = False
        os.chdir(self.pwd)

    def add_appid(self, name):
        self.appIdList.append(name)

    def add_appitem_toupload(self, item):
        self.appItemToUpload.append(item)

    def init_mesos(self):
        if not self.__mesos:
            l.info("Creating Mesos Client")
            self.__mesos = mmapi.MesosIF(self.mesos_addr)

    def init_marathon(self):
        if not self.__mt:
            l.info("Creating Marathon Client")
            self.__mt = mmapi.MarathonIF(self.marathon_addr, self.myip, self.__mesos)
            self.mt = self.__mt

    def init_appserver_dir(self):
        if not self.appserver_init_done:
            l.info("Populating the app files into directory:" + self.pwd + "/live")
            os.system("mkdir -p " + self.pwd + "/live")
            os.system("rm -f " + self.pwd + "/live/" + self.testName + ".tgz")
            os.system("cd " + self.pwd + " && tar cfz live/" + self.testName + ".tgz " + " ".join(self.appItemToUpload))
            self.appserver_init_done = True

    def start_init(self):
        self.init_mesos()
        self.init_marathon()
        l.info("Delete any pre-existing apps")
        for app in self.appIdList:
            self.delete_app(app, 12, False)
        l.info("Waiting for delete to complete")
        for app in self.appIdList:
            self.__mt.wait_app_removal(app)

    def get_appserver_addr(self):
        return self.myaddr

    def get_app_uri(self):
        return self.get_appserver_addr() + '/' + self.testName + '.tgz'

    def get_mesos_health(self):
        return self.__mesos.get_health()

    def get_mesos_version(self):
        return self.__mesos.get_version()

    def get_mesos_stats(self):
        return self.__mesos.get_stats()

    def get_mesos_slave_count(self):
        return self.__mesos.get_slave_cnt()

    def get_app_tasks(self, app):
        a1 = self.__mt.get_app(app)
        return a1.tasks

    def find_ip_uniqueapp(self, app):
        a1 = self.__mt.wait_app_ready(app, 1)
        for task in a1.tasks:
            l.info("TASK " + task.id + " Running on host : " + task.host + ' IP = ' +
                   self.__mesos.get_slave_ip_from_hn(task.host))
            return self.__mesos.get_slave_ip_from_hn(task.host)
        l.warn("Unable to find IP address for app " + app)
        return None

    def get_ip_hostname(self, hostname):
        return self.__mesos.get_slave_ip_from_hn(hostname)

    def get_cmd(self, function_path, arguments):
        return 'env && cd ./src/main/scripts && ./hydra ' + \
               function_path + ' ' + arguments

    def delete_app(self, app, timeout=1, wait=True):
        a = self.__mt.get_app(app)
        if a and (a.tasks_running > 50):
            l.info("Found %d instances of old running app. Scaling down to 1" % a.tasks_running)
            self.__mt.scale_app(app, 1)
            self.wait_app_ready(app, 1)
        if a:
            for deployment in a.deployments:
                self.__mt.delete_deployment(deployment.id)
        self.__mt.delete_app_ifexisting(app, timeout)
        if wait:
            self.__mt.wait_app_removal(app)

    def ping(self):
        return self.__mt.ping()

    def app_constraints(self, field, operator, value=None):
        return MarathonConstraint(field=field, operator=operator, value=value)

    def create_hydra_app(self, name, app_path, app_args, cpus, mem, ports=None, constraints=None):
        return self.__mt.create_app(
            name, MarathonApp(cmd=self.get_cmd(app_path, app_args),
                              cpus=cpus, mem=mem,
                              ports=ports,
                              constraints=constraints,
                              uris=[self.get_app_uri()]))

    def wait_app_ready(self, name, cnt):
        return self.__mt.wait_app_ready(name, cnt)

    def scale_app(self, name, cnt):
        return self.__mt.scale_app(name, cnt)

    def get_app(self, name):
        return self.__mt.get_app(name)

    def wait_for_interrupt(self):
        try:
            while 1:
                sys.stdout.flush()
                time.sleep(1)
        except KeyboardInterrupt:
            l.info("Exiting")
            self.stop_appserver()

    def list_tasks(self, app_id, **kwargs):
        return self.__mt.list_tasks(app_id, **kwargs)
