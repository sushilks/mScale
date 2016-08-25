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


class AppGroup(object):
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
    def __init__(self, hydra, app_name, group_name, num_app_instances, analyser=None):
        self.group_info = {}
        self.hydra = hydra
        if not analyser:
            raise Exception("AppGroup needs analyser class name passed as a name, curr val = %s" % analyser)
        self.analyser = analyser
        self.group_name = group_name
        self.app_name = app_name
        self.num_app_instances = num_app_instances
        self.group_info[self.group_name] = self.hydra.app_group[self.group_name]

    def _execute(self, method, **kwargs):
        """
        Execute provided method on self.analyser instance
        @args:
        method:    Method to execute e-g "do_ping"
        **kwargs:  kwargs to pass down to the method (Method MUST have arg implementation)
        """
        assert(self.group_name in self.hydra.app_group)
        task_list = self.group_info[self.group_name]
        for task_id in task_list:
            info = self.hydra.apps[self.app_name]['ip_port_map'][task_id]
            port = info[0]
            ip = info[1]
            ha = self.analyser(ip, port, task_id)
            l.debug("ip:port  %s:%s", ip, str(port))
            assert(method in dir(ha))
            func = getattr(ha, method)
            func(**kwargs)
            ha.stop()

    def _get_group_info(self):
        """
        Return group info
        """
        return self.group_info

    def _get_tasklist(self):
        """
        Return group tasklist
        """
        return self.group_info[self.group_name]


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
        self.apps = {}
        self.app_group = {}
        self.all_task_ids = {}
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
        self.app_id_list = []
        self.__mesos = None
        self.__mt = None
        self.appItemToUpload = app_dirs
        self.appserver_init_done = False
        BoundaryRunnerBase.__init__(self)
        if startappserver:
            self.start_appserver()
        self.all_mesos_slave_iplist = []

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
        self.app_id_list.append(name)

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
        self.delete_all_launched_apps()
        # Populate all slave ip list to be later used

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

    def get_mesos_slave_stats(self):
        return self.__mesos.get_slave_stats()

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

    def delete_app(self, app, timeout=1, wait=True, threshold=200, instance_batch=100):
        """
        Delete an application in batches to avoid overloading zookeeper, marathon
        @args:
        app:                               name of the app
        timeout:                           individual app del timeout
        wait:                              wait for app to be removed
        threshold:                         delete instance threshold
        instance_batch:                    instance batch
        """
        if app in self.apps:
            del self.apps[app]
        a = self.__mt.get_app(app)
        if a and (a.tasks_running > threshold):
            remaining = a.tasks_running
            while len(self.get_app_tasks(app)) != 1:
                # Reached required scale
                if remaining < instance_batch:
                    l.info("Approaching All instances delete for[%s] Remaining=%d", app, remaining)
                    self.__scale_app(app, 1)
                    self.wait_app_ready(app, 1)
                    assert(len(self.get_app_tasks(app)) == 1)
                    break
                target_instances = instance_batch
                l.info("Deleting batch instances=%d", target_instances)
                self.__scale_app(app, remaining - target_instances)
                self.wait_app_ready(app, remaining - target_instances)
                remaining = remaining - target_instances
                l.info("Total Remaining=%d", remaining)
        if a:
            for deployment in a.deployments:
                self.__mt.delete_deployment(deployment.id)
        self.__mt.delete_app_ifexisting(app, timeout)
        if wait:
            self.__mt.wait_app_removal(app)

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

    def create_hydra_app(self, name, app_path, app_args, cpus, mem, ports=None, constraints=None):
        """ Create an application that is a shell script.
        """
        assert(name not in self.apps)
        command = self.get_cmd(app_path, app_args)
        app_uri = self.get_app_uri()
        r = self.__mt.create_app(
            name, MarathonApp(cmd=command,
                              cpus=cpus, mem=mem,
                              ports=ports,
                              constraints=constraints,
                              uris=[app_uri]))
        self.apps[name] = {'app': r, 'type': 'script'}
        self.wait_app_ready(name, 1)
        self.refresh_app_info(name)
        return r

    def create_app_group(self, app_name, group_name, num_app_instances, analyser):
        """
        Create relevant dictionaries containting info about
        process info categorized into groups.
        @args:
        app_name:               Name of the app
        group_name:             Name of the group.
        num_app_instances:     Number of app instances to group together
        analyser:        Analyser class "name" e-g HAnalyser not HAnalyser()

        NOTE: This only groups process info like ip:port to talk to that process
              it DOES NOT group process launches
        """
        return self.create_app_instances_group(app_name, group_name, num_app_instances, analyser)

    def create_app_instances_group(self, app_name, group_name, num_app_instances, analyser):
        """
        Many instances of app can combine together to form a group. A group is just a data structure, holding,
        instance name a.k.a task name and ip:port of the app instance.
        :param app_name:            Name of the app whose instances are needed to be combined in a group.
        :param group_name:          Name of the app instances' group
        :param num_app_instances:   Number of app instances to group together.
        :param analyser:            Analyser class "name" e-g HAnalyser not HAnalyser().
        :return:                    Instance of AppGroup class.

        NOTE: This only groups process info like ip:port to talk to that process
              it DOES NOT group process launches
        """
        l.debug("Grouping process port info, name:%s group_name:%s, apps_in_group:%s, anaylzer:%s"
                % (app_name, group_name, num_app_instances, analyser))
        assert(app_name in self.apps)
        if group_name not in self.app_group:
            self.app_group[group_name] = []

        temp_list = []
        for x in range(num_app_instances):
            while True:
                key_generated = True
                r_key = random.choice(self.all_task_ids[app_name])
                l.debug("r_key = %s", r_key)
                for g_list in self.app_group.values():
                    if (r_key in g_list or r_key in temp_list):
                        key_generated = False
                        break
                if not key_generated:
                    continue
                temp_list.append(r_key)
                break
        self.app_group[group_name] = temp_list
        return AppGroup(self, app_name, group_name, num_app_instances, analyser)

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

    def scale_and_verify_app(self, name, scale_cnt, ping=True, sleep_before_next_try=1,
                             instance_batch=300, instance_threshold=500):
        """
        Scale an application to the given count
        and then wait for the application to scale and
        complete deployment.
        after that if ping is request, ping all the apps tasks
        before returning.
        Does incremental increase in scale to reduce amount of work zookeeper
        and marathon need to do
        @args:
        name:                              name of the app
        scale_cnt:                         target scale count
        ping:                              whether to ping all launched apps
        sleep_before_next_retry:           sleep time between subsequent app_get queries
        instance_batch:                    instance batch
        instance_threshold:                Max instances that could be launched in one go
        """
        l.info("Scaling %s app to [%d]", name, scale_cnt)
        assert(name in self.apps)
        instances_launched = 0
        first_batch = True
        if scale_cnt > instance_threshold:
            l.info("Requested instances=%d  > instance_threshold=%d,  breaking down scaling", scale_cnt, instance_threshold)
            while len(self.get_app_tasks(name)) != scale_cnt:
                if first_batch:
                    l.info("First batch: Launching threshold instances=%d", instance_threshold)
                    first_batch = False
                    target_instances = instance_threshold
                    self.__scale_app(name, target_instances)
                    self.wait_app_ready(name, target_instances, sleep_before_next_try)
                    remaining = scale_cnt - target_instances
                    instances_launched += target_instances
                    l.info("Total launched=%d,  Remaining=%d", instances_launched, remaining)
                    continue
                # Reached required scale
                if remaining < instance_batch:
                    l.info("Approaching required scale=%d, Total launched=%d,  Remaining=%d", scale_cnt,
                           instances_launched, remaining)
                    target_instances = remaining
                    self.__scale_app(name, instances_launched + target_instances)
                    self.wait_app_ready(name, instances_launched + target_instances, sleep_before_next_try)
                    assert(len(self.get_app_tasks(name)) == scale_cnt)
                    break
                l.info("Launching batch instances=%d", instance_batch)
                target_instances = instance_batch
                self.__scale_app(name, instances_launched + target_instances)
                self.wait_app_ready(name, instances_launched + target_instances, sleep_before_next_try)
                remaining = remaining - target_instances
                instances_launched += target_instances
                l.info("Total launched=%d,  Remaining=%d", instances_launched, remaining)
        else:
            self.__scale_app(name, scale_cnt)
            self.wait_app_ready(name, scale_cnt, sleep_before_next_try)
        inst_cnt = self.refresh_app_info(name)
        l.info("Expected count=%d,  current count=%d", scale_cnt, inst_cnt)
        assert(inst_cnt == scale_cnt)
        # probe all the clients to see if they are ready.
        if ping:
            self.ping_all_app_inst(name)

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

    def ping_all_app_inst(self, name, group_name=""):
        """
        Ping all the application task's and if any of they don't respond to
        ping remove them from active task list.
        @args:
        name:         Name of the app
        group_name:   Group name if only group singal required (optional)
        """
        assert(name in self.apps)
        task_list = self.all_task_ids[name]
        if group_name:
            assert(group_name in self.app_group)
            task_list = self.app_group[group_name]
            l.debug('Pinging group instances of app[%s], group[%s] to make sure they are started....', name, group_name)
        else:
            l.debug('Pinging instances of app[%s] to make sure they are started....', name)
        cnt = 0
        remove_list = []
        for task_id in task_list:
            info = self.apps[name]['ip_port_map'][task_id]
            port = info[0]
            ip = info[1]
            ha = HAnalyser(ip, port, task_id)
            # Signal it to start sending data, blocks until PUB responsds with "DONE" after sending all data
            res = ha.do_ping()
            if not res:
                l.info("Ping failed to [%s] %s:%s. removing from client list" % (task_id, ip, port))
                remove_list.append(task_id)
                ha.stop()
            cnt += res
            ha.stop()  # closes the Analyser socket, can not be used anymore
        l.info('Done pinging all the clients. Got pong response from %d out of %d' %
               (cnt, len(self.apps[name]['ip_port_map'].items())))

        temp_dict = {}
        for g_name in self.app_group.keys():
            temp_dict[g_name] = []
        for item in remove_list:
            l.info("Removing client [%s]" % (item))
            del self.apps[name]['ip_port_map'][item]
            self.all_task_ids[name].remove(item)
            for g_name, g_list in self.app_group.items():
                l.debug("Checking if bad client[%s] is in group[%s]", item, g_name)
                l.debug(g_list)
                if item in g_list:
                    l.info("Appending [%s] in group [%s]", item, g_name)
                    temp_dict[g_name].append(item)
        l.info(temp_dict)
        for g_name, bad_list in temp_dict.items():
            for bad_client in bad_list:
                l.info("Removing client [%s] from group [%s]", bad_client, g_name)
                self.app_group[g_name].remove(bad_client)

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

    def __scale_app(self, name, cnt):
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

    def delete_all_launched_apps(self, timeout=12):
        l.info("Delete all apps")
        for app in self.app_id_list:
            self.delete_app(app, timeout, False)
        l.info("Waiting for delete to complete")
        for app in self.app_id_list:
            self.__mt.wait_app_removal(app)

    def get_mesos_slave_ips_attr(self, attr_type, attr_value):
        """
        Get the ip of a mesos slave that matches the provided attribute
        """
        return self.__mesos.get_slave_ips_from_attribute(attr_type, attr_value)

    def get_all_mesos_slave_attr(self):
        """
        Get all slave attributes.
        """
        attr_list = []
        for idx, info in self.mesos_cluster.items():
            attr_list.append([info["cat"], info["match"]])
        # A sample attribute list would be
        # [['slave_id', 'slave-set1_0'], ['slave_id', 'slave-set1_1'], ['slave_id', 'slave-set1_2']]
        return attr_list

    def get_all_mesos_slave_iplist(self):
        """
        Get all mesos slave ips
        """
        ip_list = list()
        attr_list = self.get_all_mesos_slave_attr()
        for attr in attr_list:
            slave_ips = self.get_mesos_slave_ips_attr(attr[0], attr[1])
            if len(slave_ips) == 0:
                raise Exception("NO slave exists with attribtue [%s=%s]" % (attr[0], attr[1]))
            ip_list.append(slave_ips[0])
        return ip_list

    def get_app_mem_cpu_stats(self, name):
        """
        Get an apps stats querying all slaves
        If multiple tasks are running for the same app
        e-g an app x which is scaled to y instances.
        This function will return a list of all tasks
        stats for that app
        @args:
        name  :  Name of the app
        """
        app_stats_list = {}
        task_stats = {"timestamp": 0,
                      "mem_rss_bytes": 0,
                      "cpu_system_time_secs": 0,
                      "cpu_user_time_secs": 0,
                      }
        assert(name in self.app_id_list)
        if not self.all_mesos_slave_iplist:
            self.all_mesos_slave_iplist = self.get_all_mesos_slave_iplist()
        for slave_ip in self.all_mesos_slave_iplist:
            # list of all app and its tasks
            stats = self.__mesos.get_slave_stats(slave_ip)
            assert(stats)
            for app_task in stats:
                task_name = app_task["source"]
                if not task_name.startswith(name):
                    continue
                if slave_ip not in app_stats_list:
                    app_stats_list[slave_ip] = []
                task_stats["timestamp"] = app_task["statistics"]["timestamp"]
                task_stats["mem_rss_bytes"] = app_task["statistics"]["mem_rss_bytes"]
                task_stats["cpu_system_time_secs"] = app_task["statistics"]["cpus_system_time_secs"]
                task_stats["cpu_user_time_secs"] = app_task["statistics"]["cpus_user_time_secs"]
                app_stats_list[slave_ip].append(task_stats)
        return app_stats_list

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

