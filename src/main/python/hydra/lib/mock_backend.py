__author__ = 'AbdullahS'

from pprint import pprint, pformat   # NOQA
from hydra.lib import util
import time
import sys
import logging
import os
import random
import netifaces
from hydra.lib.childmgr import ChildManager

l = util.createlogger('MOCKAPI', logging.INFO)
# l.setLevel(logging.DEBUG)


class TaskInfo(object):
    """
    TaskInfo class that mimics marathon
    TaskInfo object.

    Note: This should not be considered a
          copy of marathon TaskInfo. Any
          required attribtue will need to be added
          on need basis.
    """
    def __init__(self):
        self.id = None
        self.ports = []


class AppInfo(object):
    """
    AppInfo class that holds information
    about launched processes.
    Instantiates ChildManager() that
    is unique to an instantiation of AppInfo object.
    """
    def __init__(self):
        # Initiate ChildManager with sighandler=False,
        # since we do not parent (in this case us) exiting
        # if a child dies
        self.cmgr = ChildManager(sighandler=False)
        self.id = None
        self.host = ""
        self.tasks = []
        self.deployments = []
        self.tasks_running = 0


class MockMarathonIF(object):
    """
    MockMarathonIF object. Exposes
    the APIs used by hydra infra.
    Governs the bookkeeping for all launched processes.

    @args:
    marathon_addr :  dummy value provided by hydra infra
    my_addr       :  dummy value provided by hydra infra
    mesos         :  MockMesosIF instance
    """
    def __init__(self, marathon_addr, my_addr, mesos):
        l.info("MockMarathonIF init")
        self.myAddr = my_addr
        self.mesos = mesos
        self.total_ports = 100
        self.port_index = 0
        self.generate_env_ports()
        self.list_apps = {}

    def generate_env_ports(self):
        """
        Generates a list of random numbers
        to be passed on to child processes as ports

        TODO (AbdullahS): There is no guarantee that
                          generated ports will be available
                          at OS level as well. See if this can
                          be improved.
        """
        self.env_ports = []
        for x in range(self.total_ports):
            self.env_ports.append(random.randrange(10000, 20000))

    def get_apps(self):
        """
        Return list of all launched apps
        """
        return self.list_apps

    def get_app(self, app_id):
        """
        Return AppInfo object for respective app

        @args:
        app_id : unique app id
        """
        if app_id in self.list_apps:
            return self.list_apps[app_id]
        l.info("No app named [%s] exists", app_id)
        return None

    def delete_app(self, app_id, force=False):
        """
        Delete app, terminates all child processes

        @args:
        app_id : unique app id
        force  : unused, hydra infra compatibility
        """
        l.info("Deleting [%s]", app_id)
        a = self.get_app(app_id)
        a.cmgr.terminate_process_and_children(app_id)
        del self.list_apps[app_id]

    def delete_deployment(self, dep_id):
        return

    def get_deployments(self):
        return

    def delete_app_ifexisting(self, app_id, trys=4):
        """
        Delete app if existing terminates all child processes

        @args:
        app_id : unique app id
        trys   : retry count
        """
        for idx in range(0, trys):
            try:
                a = self.get_app(app_id)
                if a:
                    return self.delete_app(app_id)
                return None
            except:
                e = sys.exc_info()[0]
                pprint("<p>Error: %s</p>" % e)
                time.sleep(10)
        raise

    def create_app(self, app_id, attr):
        """
        Launch the requested app by hydra infra
        Uses ChildManager inside AppInfo to launch
        child processes as tasks.

        @args:
        app_id : unique app id
        attr   : hydra MarathonApp instance, creates all app attributes
        """
        # Prepare process data
        cmd = attr.cmd
        requested_ports = len(attr.ports)
        cmd = cmd[cmd.rfind("./hydra"):len(cmd)]
        cmd = "hydra " + cmd[cmd.find(' '): len(cmd)].strip()
        cmd = cmd.split(' ')
        pwd = os.getcwd()
        cwd = None
        l.info("CWD = " + pformat(pwd))
        l.info("CMD = " + pformat(cmd))

        # Prepare ports data, mimic marathon.. sort of
        myenv = os.environ.copy()
        requested_ports = len(attr.ports)
        curr_ports = []
        for x in range(requested_ports):
            myenv["PORT%d" % x] = str(self.env_ports[self.port_index])
            curr_ports.append(str(self.env_ports[self.port_index]))
            self.port_index += 1

        # Init app info
        app_info = AppInfo()
        myenv["mock"] = "true"
        app_info.cmgr.add_child(app_id, cmd, cwd, myenv)
        app_info.cmgr.launch_children(ports=curr_ports)
        app_info.tasks_running = 1

        # Init task info, sort of mimics marathon
        app_info.tasks.append(TaskInfo())
        app_info.tasks[0].id = str(app_info.cmgr.jobs[app_id]["pid"])
        app_info.tasks[0].ports = app_info.cmgr.jobs[app_id]["ports"]
        app_info.tasks[0].host = "localhost"
        self.list_apps[app_id] = app_info

    def wait_app_removal(self, app):
        """
        Wait for app to be removed

        @args:
        app :  unique app name
        """
        cnt = 0
        while True:
            if not self.get_app(app):
                break
            time.sleep(0.2)
            cnt += 1
            if cnt > 0:
                l.info("Stuck waiting for %s to be deleted CNT=%d" % (app, cnt))
        return True

    def wait_app_ready(self, app, running_count):
        """
        Wait for app to be ready

        @args:
        app            :  Unique app name
        running_count  :  Expected app running count
        """
        cnt = 0
        while True:
            a1 = self.get_app(app)
            if a1.tasks_running == running_count:
                return a1
            cnt += 1
            time.sleep(1)
            if (cnt % 30) == 29:
                l.info("Waiting for app [%s] to launch", app)

    def scale_app(self, app, scale):
        # TODO: (AbdullahS) See if it makes sense to implement scale_app
        return True


class MockMesosIF(object):
    """
    MockMesosIF class.
    Creates a mapping of only one slave i-e localhost
    """
    def __init__(self, addr):
        self.slaves_ids = {}
        self.slaves_hostname_info = {}
        self.slave_count = 1
        self.myaddr = addr
        # TODO: (AbdullahS): read the device from config
        self.mydev = "eth0"
        self.myip = netifaces.ifaddresses(self.mydev)[2][0]["addr"]
        self.update_slaves()
        l.info("MockMesosIF init")

    def update_slaves(self):
        """
        Populate localhost data
        """
        self.total_slaves = self.slave_count
        self.slaves_hostname_info["localhost"] = self.myip
        l.info(self.slaves_hostname_info)

    def get_slave_ip_from_hn(self, slave_hn):
        """
        Return ip for hostname (localhost)

        @args:
        slave_hn  : slave hostname
        """
        return self.slaves_hostname_info[slave_hn]
