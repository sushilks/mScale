__author__ = 'AbdullahS'

from pprint import pprint, pformat   # NOQA
from hydra.lib import util
import time
import sys
import logging
import os
import random
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
        self.app_attr = {}

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
        l.info(a)
        a.cmgr.terminate_process_and_children(app_id)
        if self.app_attr[app_id][1] > 1:
            scale_app_name = app_id + "-scale"
            a.cmgr.terminate_process_and_children(scale_app_name)
        del self.list_apps[app_id]
        del self.app_attr[app_id]

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

    def create_app(self, app_id, attr, app_local_launch_name=""):
        """
        Launch the requested app by hydra infra
        Uses ChildManager inside AppInfo to launch
        child processes as tasks.

        @args:
        app_id                  : unique app id
        attr                    : hydra MarathonApp instance, creates all app attributes
        app_local_launch_name   : Launch name for the app, needs to be different for subsequent
                                  launches e-g scaling app
        """
        # Prepare process data
        if not app_local_launch_name:
            app_local_launch_name = app_id
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
        if app_id not in self.list_apps:
            self.list_apps[app_id] = app_info
        if app_id not in self.app_attr:
            self.app_attr[app_id] = [attr, 0]  # task index
        myenv["mock"] = "true"

        # launch children
        self.list_apps[app_id].cmgr.add_child(app_local_launch_name, cmd, cwd, myenv)
        self.list_apps[app_id].cmgr.launch_children(ports=curr_ports)

        # Init task info, sort of mimics marathon
        self.list_apps[app_id].tasks.append(TaskInfo())
        task_count = self.app_attr[app_id][1]
        self.list_apps[app_id].tasks[task_count].id = str(self.list_apps[app_id].cmgr.jobs[app_local_launch_name]["pid"])
        self.list_apps[app_id].tasks[task_count].ports = self.list_apps[app_id].cmgr.jobs[app_local_launch_name]["ports"]
        self.list_apps[app_id].tasks[task_count].host = "localhost"
        self.list_apps[app_id].tasks_running = len(self.list_apps[app_id].tasks)
        self.app_attr[app_id][1] += 1

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
        l.info("Mock scale app")
        scale_app_name = app + "-scale"
        attr = self.app_attr[app][0]
        self.create_app(app, attr, app_local_launch_name=scale_app_name)
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
        self.myip = "127.0.0.1"
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
