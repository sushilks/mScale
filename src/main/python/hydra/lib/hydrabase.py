__author__ = 'sushil'

import netifaces
import logging
import os
import time
import sys
import code
import traceback
import signal
import random
from random import randint
from pprint import pprint, pformat  # NOQA
from hydra.lib import appserver, mmapi, util, mock_backend
from hydra.lib.boundary import BoundaryRunnerBase
from hydra.lib.h_analyser import HAnalyser
from hydra.lib import common
from ConfigParser import ConfigParser

l = util.createlogger('HydraBase', logging.INFO)
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

class HydraApp(object):
    def __init__(self, hydra_app_name, app_path, app_args, cpus, mem, ports, hydra, binary=True):
        self.hydra_app_name = hydra_app_name
        self.app_path = app_path
        self.cpus = cpus
        self.mem = mem
        self.ports = ports
        self.hydra = hydra

        if binary:
            self.command = app_path
        else:
            self.command = self.hydra.get_cmd(app_path, app_args)
        self.app_uri = self.hydra.get_app_uri()
        # Number of marathon apps under this Hydra App.
        self.num_mt_apps = 0
        # Marathon apps dictionary. key:mt_app_name value:mt_app(dict)
        self.mt_apps = dict()
        # Taks groups under HydraApp. key:group_name value:group_obj
        self.tasks_groups = dict()

    def create(self):
        slaves_count = self.hydra.get_mesos_slave_count()
        l.info("slaves_count:%s" % slaves_count)
        for slave_num in range(slaves_count):
            field = self.hydra.mesos_cluster[slave_num]['cat']
            value = self.hydra.mesos_cluster[slave_num]['match']
            l.info("field:%s, value:%s" % (field, value))

            constraints = [self.hydra.app_constraints(field=field, operator='CLUSTER', value=value)]
            mt_app_name = self.hydra_app_name + "-" + str(slave_num)
            r = self.hydra.mt.create_app(mt_app_name,
                                         MarathonApp(cmd=self.command, cpus=self.cpus, mem=self.mem,
                                                     ports=self.ports, constraints=constraints,
                                                     uris=[self.app_uri]))
            self.hydra.wait_app_ready(mt_app_name, 1)

            # populate data structures
            self.num_mt_apps += 1
            mt_app = dict()
            mt_app["obj"] = r
            mt_app["tasks"] = dict()
            self.mt_apps[mt_app_name] = mt_app
        self.refresh_tasks_info()

    def delete(self, wait=True):
        # TODO:             self.num_mt_apps -= 1
        for mt_app_name, mt_app in self.mt_apps:
            a = self.hydra.mt.get_app(mt_app_name)
            if a and (a.tasks_running > 50):
                l.info("Found %d instances of old running app. Scaling down to 1" % a.tasks_running)
                self.hydra.mt.scale_app(mt_app_name, 1)
                self.hydra.wait_app_ready(mt_app_name, 1)
            if a:
                for deployment in a.deployments:
                    self.hydra.mt.delete_deployment(deployment.id)
            self.hydra.mt.delete_app_ifexisting(mt_app_name, timeout=2)
            if wait:
                self.hydra.mt.wait_app_removal(mt_app_name)

    def get_round_robin_number_list(self, number, num_entities):
        quotient = number / num_entities
        reminder = number % num_entities
        round_robin_number = [quotient] * num_entities
        for i in range(reminder):
            round_robin_number[i] += 1

        return round_robin_number

    def scale(self, num_tasks, policy):
        policy_type = policy["type"]
        slave_list = policy["slave_list"]
        num_slaves = len(slave_list)

        l.info("policy_type:%s, slave_list:%s, num_slaves:%s" %(policy_type, slave_list, num_slaves))
        if policy_type == "RR":
            num_tasks_on_slave = self.get_round_robin_number_list(num_tasks, num_slaves)
            for i in range(num_slaves):
                scale_count = num_tasks_on_slave[i]
                slave_num = slave_list[i]
                mt_app_name = self.hydra_app_name + "-" + str(slave_num)
                self.hydra.scale_app(mt_app_name, scale_count)
                self.hydra.wait_app_ready(mt_app_name, scale_count, sleep_before_next_try=2)
            self.refresh_tasks_info()

    def get_all_tasks(self):
        all_tasks = dict()
        mt_apps_name = self.mt_apps.keys()
        for mt_app_name in mt_apps_name:
            mt_app_tasks = self.mt_apps[mt_app_name]["tasks"]
            all_tasks.update(mt_app_tasks)
        return all_tasks

    def get_all_tasks_on_particular_slaves(self, slave_list):
        all_tasks_on_particular_slaves = dict()
        for slave_num in slave_list:
            mt_app_name = self.hydra_app_name + "-" + str(slave_num)
            mt_app_tasks = self.mt_apps[mt_app_name]["tasks"]
            all_tasks_on_particular_slaves.update(mt_app_tasks)
        return all_tasks_on_particular_slaves

    def get_lonelier_tasks_on_particular_slaves(self, slave_list):
        lonelier_tasks_on_particular_slaves = dict()
        for slave_num in slave_list:
            lonelier_tasks_on_particular_slaves[slave_num] = dict()
            mt_app_name = self.hydra_app_name + "-" + str(slave_num)
            mt_app_tasks = self.mt_apps[mt_app_name]["tasks"]
            for task_name, task_info in mt_app_tasks.items():
                if task_info["group"] is None:
                    lonelier_tasks_on_particular_slaves[slave_num][task_name] = task_info

        return lonelier_tasks_on_particular_slaves

    def refresh_tasks_info(self):
        for mt_app_name, mt_app in self.mt_apps.items():
            mt_app_tasks = mt_app["tasks"]
            tasks = self.hydra.get_app_tasks(mt_app_name)
            for task in tasks:
                task_host = task.host
                task_ip = self.hydra.get_ip_hostname(task_host)
                for task_rep_port in task.ports:
                    task_name = task.id + '_PORT' + str(task_rep_port)
                    task_info = mt_app_tasks.get(task_name)
                    if task_info is None:
                        task_info = {"host": task_host, "ip": task_ip, "rep_port": task_rep_port,
                                     "stats": None, "group": None}
                    else:
                        task_info["host"] = task_host
                        task_info["ip"] = task_ip
                        task_info["rep_port"] = task_rep_port

                    mt_app_tasks[task_name] = task_info

    def remove_non_responsive_tasks(self):
        non_responsive_tasks = self.get_non_responsive_tasks()
        for mt_app_name, non_responsive_tasks_name_list in non_responsive_tasks.items():
            for non_responsive_task_name in non_responsive_tasks_name_list:
                del self.mt_apps[mt_app_name]["tasks"][non_responsive_task_name]

    def get_non_responsive_tasks(self):
        non_responsive_tasks = dict()
        for mt_app_name, mt_app in self.mt_apps.items():
            non_responsive_tasks[mt_app_name] = list()
            for task_name, task_info in mt_app["tasks"].items():
                port = task_info["rep_port"]
                ip = task_info["ip"]
                ha = HAnalyser(ip, port, task_name)
                res = ha.do_ping()
                if not res:
                    l.info("Ping failed to [%s] %s:%s. removing from client list" % (task_name, ip, port))
                    non_responsive_tasks[mt_app_name].append(task_name)
                ha.stop()
        return non_responsive_tasks


class TasksGroup(object):
    """
    Class to hold info about an APP group.
    Allows cabilities to execute methods on the analyser
    as passed by the caller
    @args:
    hydra:          hydra handle
    app_name:       App name
    group_name:     group name
    analyser:       Analyser class "name" e-g HAnalyser not HAnalyser()
    """
    def __init__(self, hydra, hydra_app_name, tasks_group_name, analyser=None):
        self.hydra = hydra
        self.hydra_app_name = hydra_app_name
        self.tasks_group_name = tasks_group_name
        self.num_tasks = 0
        if not analyser:
            raise Exception("AppGroup needs analyser class name passed as a name, curr val = %s" % analyser)
        self.analyser = analyser
        self.tasks_group = dict()

    def add_tasks_to_group(self, num_tasks, policy):
        policy_type = policy["type"]
        slave_list = policy["slave_list"]
        num_slaves = len(slave_list)

        hydra_app = self.hydra.hydra_apps[self.hydra_app_name]
        hydra_app.scale(num_tasks, policy)
        hydra_app.remove_non_responsive_tasks()

        lonelier_tasks = hydra_app.get_lonelier_tasks_on_particular_slaves(slave_list)

        if policy_type == "RR":
            lst_desired_num_tasks_on_slave = hydra_app.get_round_robin_number_list(num_tasks, num_slaves)
            for i in range(num_slaves):
                slave_num = slave_list[i]
                desired_num_tasks_on_slave = lst_desired_num_tasks_on_slave[i]
                lonlier_tasks_of_slave = lonelier_tasks[i]
                j = 0
                for task_name, task_info in lonlier_tasks_of_slave.items():
                    self.tasks_group[task_name] = task_info
                    self.num_tasks += 1
                    j += 1
                    if j == desired_num_tasks_on_slave:
                        break
        hydra_app.tasks_groups[self.tasks_group_name] = self.tasks_group

    def _execute(self, method, **kwargs):
        """
        Execute provided method on self.analyser instance
        @args:
        method:    Method to execute e-g "do_ping"
        **kwargs:  kwargs to pass down to the method (Method MUST have arg implementation)
        """
        hydra_app = self.hydra.hydra_apps[self.hydra_app_name]
        assert(self.tasks_group_name in hydra_app.tasks_groups)
        task_list = self.tasks_group
        for task_name, task_info in task_list:
            port = task_info["rep_port"]
            ip = task_info["ip"]
            ha = self.analyser(ip, port, task_name)
            l.debug("ip:port  %s:%s", ip, str(port))
            assert(method in dir(ha))
            func = getattr(ha, method)
            func(**kwargs)
            ha.stop()

class HydraBase(BoundaryRunnerBase):
    def __init__(self, test_name, options, config=None,
                 startappserver=True, mock=False, app_dirs=['target', 'src']):
        if not config:
            config = ConfigParser()
        config_filename = 'hydra.ini'
        if hasattr(options, 'config_file'):
            config_filename = options.config_file
        if not os.path.isfile(config_filename):
            l.error("Unable to open config file %s" % config_filename)
            raise Exception("Unable to open config file %s" % config_filename)
        cwd = ""
        if hasattr(options, 'live_dir'):
            cwd = options.live_dir
        config.read(config_filename)
        self.pwd = os.getcwd()
        if cwd:
            self.pwd = cwd
        self.testName = test_name
        self.appserver_running = False
        self.myport = config.getint('hydra', 'port')
        self.mydev = config.get('hydra', 'dev')
        self.myip = netifaces.ifaddresses(self.mydev)[2][0]['addr']
        self.myaddr = 'http://' + self.myip + ':' + str(self.myport)
        self.config = config
        self.options = options
        self.hydra_apps = {}
        self.mock = mock
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
        self.app_prefix = config.get('marathon', 'app_prefix')
        self.appIdList = []
        self.__mesos = None
        self.__mt = None
        self.appItemToUpload = app_dirs
        self.appserver_init_done = False
        BoundaryRunnerBase.__init__(self)
        if startappserver:
            self.start_appserver()

    def set_options(self, options):
        self.options = options

    def format_appname(self, name):
        return self.app_prefix + name

    def start_appserver(self):
        self.init_appserver_dir()
        if not self.appserver_running:
            self.myserver = appserver.TServer(self.myport, self.pwd + '/live')
            self.myserver.start()
            self.appserver_running = True

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
            if self.mock:
                l.info("Initating MockMesosIF")
                self.__mesos = mock_backend.MockMesosIF(self.mesos_addr)
            else:
                self.__mesos = mmapi.MesosIF(self.mesos_addr)

    def init_marathon(self):
        if not self.__mt:
            l.info("Creating Marathon Client")
            if self.mock:
                l.info("Initating MockMarathonIF")
                self.__mt = mock_backend.MockMarathonIF(self.marathon_addr, self.myip, self.__mesos)
            else:
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
        self.delete_all_launched_hydra_apps(timeout=5)

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
        """ Get a list of tasks for the apps
        """
        a1 = self.__mt.get_app(app)
        return a1.tasks

    def get_ip_hostname(self, hostname):
        """ Get the ip of a mesos slave
        """
        return self.__mesos.get_slave_ip_from_hn(hostname)

    def get_cmd(self, function_path, arguments):
        return 'env && cd ./src/main/scripts && ./hydra ' + \
               function_path + ' ' + arguments

    def ping(self):
        return self.__mt.ping()

    def app_constraints(self, field, operator, value=None):
        """
        Constraints control where apps run. It is to allow optimizing for either fault tolerance (by spreading a task
        out on multiple nodes) or locality (by running all of an application tasks on the same node). Constraints have
        three parts
        :param field: Field can be the hostname of the agent node or any attribute of the agent node.
        :param operator: e.g. UNIQUE tells Marathon to enforce uniqueness of the attribute across all of an app's tasks.
                              This allows you, for example, to run only one app taks on each host.
                              CLUSTER allows you to run all of your app's tasks on agent nodes that share a certain
                              attribute. Think about having special hardware needs.
                              GROUP_BY can be used to distribute tasks evenly across racks or datacenters for high
                              availibility.
                              LIKE accepts a regular expression as parameter, and allows you to run your tasks only on
                              the agent nodes whose field values match the regular expression.
                              UNLIKE accepts a regular expression as parameter, and allows you to run your tasks on
                              agent nodes whose field values do NOT match the regular expression.
        :param value:
        :return:
        """
        return MarathonConstraint(field=field, operator=operator, value=value)

    def create_hydra_app(self, hydra_app_name, app_path, app_args, cpus, mem, ports=None):
        """
        Create an application that is a shell script.
        """
        assert (hydra_app_name not in self.hydra_apps)
        hydra_app = HydraApp(hydra_app_name, app_path, app_args, cpus, mem, ports, self)
        hydra_app.create()
        self.hydra_apps[hydra_app_name] = hydra_app

    def delete_hydra_app(self, hydra_app_name):
        if hydra_app_name in self.hydra_apps:
            hydra_app = self.hydra_apps[hydra_app_name]
            hydra_app.delete()

    def create_hydra_app_tasks_group(self, hydra_app_name, tasks_group_name, num_tasks, policy, analyser):
        tasks_group = TasksGroup(self, hydra_app_name, tasks_group_name, analyser)
        tasks_group.add_tasks_to_group(num_tasks, policy)
        return tasks_group

    def ping_all_hydra_app_inst(self, hydra_app_name):
        """
        Ping all the application task's and if any of they don't respond to
        ping remove them from active task list.
        @args:
        name:         Name of the app
        group_name:   Group name if only group singal required (optional)
        """
        assert (hydra_app_name not in self.hydra_apps)
        hydra_app = self.hydra_apps[hydra_app_name]
        hydra_app.ping_all_instances()

    def create_binary_app(self, name, app_script, cpus, mem, ports=None, constraints=None):
        """ Create an application that is a binary and not a shell script.
        """
        assert(name not in self.apps)
        r = self.__mt.create_app(
            name, MarathonApp(cmd=app_script,
                              cpus=cpus, mem=mem,
                              ports=ports,
                              constraints=constraints,
                              uris=[self.get_app_uri()]))
        self.apps[name] = {'app': r, 'type': 'binary'}
        self.wait_app_ready(name, 1)
        self.refresh_app_info(name)
        return r

    def scale_and_verify_app(self, mt_app_name, scale_count, sleep_before_next_try=1):
        self.__scale_app(mt_app_name, scale_count)
        self.hydra.wait_app_ready(mt_app_name, scale_count, sleep_before_next_try=2)

    def reset_all_app_stats(self, name, group_name=""):
        """
        Reset all the stats for an application
        @args:
        name:         Name of the app
        group_name:   Group name if only group singal required (optional)
        """
        assert(name in self.apps)
        task_list = self.all_task_ids[name]
        if group_name:
            assert(group_name in self.app_group)
            task_list = self.app_group[group_name]
            l.info("Attempting to reset client group stats for app[%s], group[%s]...", name, group_name)
        else:
            l.info("Attempting to reset client stats for app[%s]...", name)
        for task_id in task_list:
            info = self.apps[name]['ip_port_map'][task_id]
            port = info[0]
            ip = info[1]
            ha_sub = HAnalyser(ip, port, task_id)
            # Signal it to reset all client stats
            ha_sub.reset_stats()
            ha_sub.stop()  # closes the ANalyser socket, can not be used anymore

    def refresh_app_info(self, name):
        """ Refresh all the ip-port map for the application
        This is done by talking to marathon and getting the list of tasks
        """
        assert(name in self.apps)
        self.apps[name] = {'ip_port_map': {},
                           'stats': {},
                           'property': {}}
        ip_port_map = self.apps[name]['ip_port_map']
        tasks = self.get_app_tasks(name)
        for task in tasks:
            app_ip = self.get_ip_hostname(task.host)
            for app_rep_port in task.ports:
                ip_port_map[task.id + '_PORT' + str(app_rep_port)] = \
                    [app_rep_port, app_ip]
        self.all_task_ids[name] = self.apps[name]["ip_port_map"].keys()
        return len(tasks)

    def fetch_app_stats(self, name, group_name=""):
        """
        Fetch stats from all the instances of the
        app and store it locally.
        The stats collection is done while looking at "msg_cnt"
        so it's mandatory that all the stats are required to have a field msg_cnt
        while collecting the msg_cnt is monitored, and stats collection is completed
        when the msg_cnt stops increasing between two successive reads.
        @args:
        name:         Name of the app
        group_name:   Group name if only group singal required (optional)
        """
        assert(name in self.apps)
        task_list = self.all_task_ids[name]
        if group_name:
            assert(group_name in self.app_group)
            task_list = self.app_group[group_name]
            l.info("Attempting to fetch client group stats for app[%s], group[%s]...", name, group_name)
        else:
            l.info("Attempting to fetch client stats for app[%s]...", name)
        self.apps[name]['stats'] = {}
        first_itr = True
        no_delay_needed_count = 0
        for task_id in task_list:
            info = self.apps[name]['ip_port_map'][task_id]
            port = info[0]
            ip = info[1]
            ha_sub = HAnalyser(ip, port, task_id)
            # Signal it to start sending data, blocks until PUB responsds with "DONE" after sending all data
            stats = ha_sub.get_stats()
            while first_itr:
                time.sleep(.1)
                stats2 = ha_sub.get_stats()
                #  if it's the first read make sure that the sub has stopped receiving data
                if (stats['msg_cnt'] == stats2['msg_cnt']):
                    # first_itr = False
                    no_delay_needed_count += 1
                    if (no_delay_needed_count > 40):
                        # No more delays if 100 successive read's where
                        # stable on msg_cnt
                        first_itr = False
                    break
                no_delay_needed_count = 0
                stats = stats2
            ha_sub.stop()  # closes the ANalyser socket, can not be used anymore
            stats['task_id'] = task_id
            self.apps[name]['stats'][str(ip) + ':' + str(port)] = stats  # copy.deepcopy(stats)

    def get_app_ipport_map(self, name):
        """ Get the IP PORT map for all the instances
        for the app.
        """
        assert(name in self.apps)
        return self.apps[name]['ip_port_map']

    def get_app_stats(self, name):
        """ Get the stats associated with the application
        """
        assert(name in self.apps)
        return self.apps[name]['stats']

    def get_app_property(self, name, pname):
        """ Get a property for an app
        """
        assert(name in self.apps)
        if pname in self.apps[name]['property']:
            return self.apps[name]['property'][pname]
        return None

    def set_app_property(self, name, key, value):
        """ Set a property for the APP
        i.e. for app "name" add property Prop[key]=value
        """
        assert(name in self.apps)
        self.apps[name]['property'][key] = value

    def get_app_instcnt(self, name):
        """ Get the number of instances an application has
        """
        assert(name in self.apps)
        return len(self.apps[name]['ip_port_map'])

    def wait_app_ready(self, name, cnt, sleep_before_next_try=1):
        """ Wait till the application has as many instances as 'cnt'
        """
        return self.__mt.wait_app_ready(name, cnt, sleep_before_next_try)

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

    def delete_all_launched_hydra_apps(self, cmd=None, timeout=1, wait=True):
        apps = self.__mt.get_apps()
        for app in apps:
            app_id = app.id
            if app.tasks_running > 50:
                l.info("Found %d instances of old running app. Scaling down to 1" % a.tasks_running)
                self.__mt.scale_app(app_id, 1)
                self.wait_app_ready(app_id, 1)
                if app:
                    for deployment in app.deployments:
                        self.__mt.delete_deployment(deployment.id)
            self.__mt.delete_app_ifexisting(app_id, timeout)
            if wait:
                self.__mt.wait_app_removal(app_id)
        # TODO: DataSturcture cleanup.
        for hydra_app_name, hydra_app in self.hydra_apps.items():
            hydra_app.mt_apps.clear()
            hydra_app.tasks_groups.clear()
        self.hydra_apps.clear()

    def random_select_instances(self, app_name, cnt):
        """ Select a random collection of tasks for an app
        and and return the set
        """
        ipm = self.get_app_ipport_map(app_name)
        cset = []
        assert(cnt < len(ipm))
        for idx in range(0, cnt):
            r = randint(0, len(ipm) - 1)
            cset += [ipm.keys()[r]]
        return cset

    def get_mesos_slave_ips_attr(self, attr_type, attr_value):
        """
        Get the ip of a mesos slave that matches the provided attribute
        """
        return self.__mesos.get_slave_ips_from_attribute(attr_type, attr_value)

    @staticmethod
    def block_ip_port_on_node(ip_to_block, port, chain="INPUT", protocol="tcp", host_ip="", user=""):
        """
        Blocks all incoming communication from an ip on a host (local or remote)
        @args:
        ip_to_block:     IP to block
        port:            Port to block
        chain:           rule chain, INPUT, OUTPUT
        protocol:        tcp, udp
        host_ip:         Host to put this iptable rule on (Default executes on localhost)
        user:            Remote user

        """
        l.info("Attempting to block all communication from ip:port [%s:%s]", ip_to_block, port)
        # Block all incoming traffic from ip_to_block
        cmd = "sudo /sbin/iptables -A %s -p %s --destination-port %s -s %s -j DROP" \
              % (chain, protocol, port, ip_to_block)
        if host_ip and user:
            common.execute_remote_cmd(host_ip, user, cmd)
        else:
            common.execute_local_cmd(cmd)

    @staticmethod
    def unblock_ip_port_on_node(ip_to_unblock, port, chain="INPUT", protocol="tcp", host_ip="", user=""):
        """
        Blocks  all incoming communication from an ip on a host (local or remote)
        @args:
        ip_to_block:     IP to block
        port:            Port to block
        chain:           rule chain, INPUT, OUTPUT
        protocol:        tcp, udp
        host_ip:         Host to put this iptable rule on (Default executes on localhost)
        user:            Remote user
        """
        l.info("Attempting to UNblock all communication from ip:port [%s:%s]", ip_to_unblock, port)
        # Block all incoming traffic from ip_to_block
        cmd = "sudo /sbin/iptables -D %s -p %s --destination-port %s -s %s -j DROP" \
              % (chain, protocol, port, ip_to_unblock)
        if host_ip and user:
            common.execute_remote_cmd(host_ip, user, cmd)
        else:
            common.execute_local_cmd(cmd)

    def find_ip_uniqueapp(self, app):
        a1 = self.__mt.wait_app_ready(app, 1)
        for task in a1.tasks:
            l.info("TASK " + task.id + " Running on host : " + task.host + ' IP = ' +
                   self.__mesos.get_slave_ip_from_hn(task.host))
            return self.__mesos.get_slave_ip_from_hn(task.host)
        l.warn("Unable to find IP address for app " + app)
        return None
