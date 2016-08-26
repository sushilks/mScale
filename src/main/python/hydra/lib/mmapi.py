__author__ = 'sushil'

from marathon import MarathonClient
from pprint import pprint, pformat   # NOQA
from hydra.lib import util
import marathon
import requests
import json
import time
import sys
import logging
import re
import traceback

l = util.createlogger('API', logging.INFO)
# l.setLevel(logging.DEBUG)


class MarathonIF(object):
    def __init__(self, marathon_addr, my_addr, mesos):
        self.mcli = MarathonClient(marathon_addr)
        self.myAddr = my_addr
        self.mesos = mesos

    def get_apps(self):
        listapps = self.mcli.list_apps()
        return listapps

    def get_app(self, app_id, timeout=300):
        st_time = time.time()
        while(time.time() - st_time < timeout):
            try:
                try:
                    a = self.mcli.get_app(app_id)
                except marathon.exceptions.NotFoundError as e:  # NOQA
                    return None
                return a
            except:
                l.info("mcli: get_app returned error")
                l.info(traceback.format_exc())
                l.info("Retrying after 10 secs timeout=%d", timeout)
                time.sleep(10)
        raise Exception("mcli get_app timed out, possible zookeper/marathon/mesos malfunction")

    def delete_app(self, app_id, force=False, timeout=200):
        st_time = time.time()
        while(time.time() - st_time < timeout):
            try:
                self.mcli.delete_app(app_id, force)
                return
            except:
                l.info("mcli: delete_app returned error")
                l.info(traceback.format_exc())
                l.info("Retrying after 10 secs timeout=%d", timeout)
                time.sleep(10)
        raise Exception("mcli delete_app timed out, possible zookeper/marathon/mesos malfunction")

    def delete_deployment(self, dep_id):
        return self.mcli.delete_deployment(dep_id)

    def get_deployments(self):
        return self.mcli.list_deployments()

    def delete_app_ifexisting(self, app_id, trys=4):
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

    @staticmethod
    def is_valid_app_id(app_id):
        # allowed: lowercase letters, digits, hyphens, slash, dot
        if re.match("^[A-Za-z0-9-/.]*$", app_id):
            return True
        return False

    def create_app(self, app_id, attr):
        """
            Create and start an app.
            :param app_id: (str) - Application ID
            :param attr: marathon.models.app.MarathonApp application to create.
            :return: the created app
        """
        # Validate that app_id conforms to allowed naming scheme.
        if not self.is_valid_app_id(app_id):
            l.error("Error: Only lowercase letters, digits, hyphens are allowed in app_id. %s" % app_id)
            raise Exception("Invalid app_id")

        for idx in range(0, 10):
            try:
                a = self.mcli.create_app(app_id, attr)
                return a
            except marathon.exceptions.MarathonHttpError as e:
                if str(e).find('App is locked by one or more deployments. Override with the option') >= 0:
                    time.sleep(1)
                else:
                    raise
        raise

    def wait_app_removal(self, app):
        cnt = 0
        while True:
            if not self.get_app(app):
                break
            time.sleep(0.2)
            cnt += 1
            if cnt > 0:
                l.info("Stuck waiting for %s to be deleted CNT=%d" % (app, cnt))
        return True

    def wait_app_ready(self, app, running_count, sleep_before_next_try=1):
        cnt = 0
        while True:
            a1 = self.get_app(app)
            # if tasks_running are greater (due to whatever reason, scale down accordingly)
            if a1.tasks_running > running_count:
                delta = a1.tasks_running - running_count
                l.info("Found [%d] more apps, scaling down to [%d]", delta, running_count)
                self.scale_app(app, running_count)
                # Allow for some time before next poll
                time.sleep(1)
                continue
            if a1.tasks_running == running_count:
                return a1
            cnt += 1
            time.sleep(sleep_before_next_try)
            if (cnt % 30) == 29:
                l.info("[%d]Waiting for task to move to running stage, " % cnt +
                       "current stat staged=%d running=%d expected Running=%d" %
                       (a1.tasks_staged, a1.tasks_running, running_count))

    def scale_app(self, app, scale, timeout=300):
        st_time = time.time()
        while(time.time() - st_time < timeout):
            try:
                self.mcli.scale_app(app, scale)
                return
            except:
                l.info("mcli: scale_app returned error")
                l.info(traceback.format_exc())
                l.info("Retrying after 10 secs timeout=%d", timeout)
                time.sleep(10)
        raise Exception("mcli scale_app timed out, possible zookeper/marathon/mesos malfunction")

    def ping(self):
        return self.mcli.ping()


class MesosIF(object):
    def __init__(self, addr):
        self.myaddr = addr
        self.update_slaves()

    def update_slaves(self):
        r = requests.get(self.myaddr + '/master/slaves')
        assert r.status_code == 200
        dt = json.loads(r.content.decode("utf-8"))
        self.noOfSlaves = len(dt['slaves'])
        # pprint(" Slaves Found : " + str(self.noOfSlaves))
        self.slavesID = {}
        self.slavesHN = {}
        for idx in range(0, self.noOfSlaves):
            itm = dt['slaves'][idx]
            # l.info(" Slave [" + itm['hostname'] + " ID=" + itm['id'] +
            #       "  CPU = " + str(itm['used_resources']['cpus']) + '/' + str(itm['unreserved_resources']['cpus']))
            self.slavesHN[itm['hostname']] = itm
            self.slavesID[itm['id']] = itm

    def get_health(self):
        r = requests.get(self.myaddr + '/master/state')
        if (r.status_code == 200):
            return True
        return False

    def get_slave_stats(self, ip, port=5051):
        """
        Get slave statistics via mesos API
        @args:
        ip:      Ip of the slave
        port:    Port that slave is listening to for requests
        """
        addr = "http://%s:%d" % (ip, port)
        # returns a list of app tasks
        r = requests.get(addr + '/monitor/statistics.json')
        assert(r.status_code == 200)
        dt = json.loads(r.content.decode("utf-8"))
        return dt

    def get_version(self):
        # returns
        # {"build_date":"2016-02-23 00:35:03","build_time":1456187703.0,"build_user":"root",
        #  "git_sha":"864fe8eabd4a83b78ce9140c501908ee3cb90beb","git_tag":"0.27.1","version":"0.27.1"}
        r = requests.get(self.myaddr + '/version')
        if (r.status_code == 200):
            return json.loads(r.content.decode("utf-8"))
        raise Exception('Unable to read version information from Mesos StatusCode:' + str(r.status_code))

    def get_stats(self):
        # returns
        # {"avg_load_15min":0.24,"avg_load_1min":0.07,"avg_load_5min":0.18,
        #  "cpus_total":4,"mem_free_bytes":1114415104,"mem_total_bytes":15770980352}
        r = requests.get(self.myaddr + '/system/stats.json')
        if (r.status_code == 200):
            return json.loads(r.content.decode("utf-8"))
        return None

    def print_slaves(self):
        for slaveId in self.slavesID.keys():
            itm = self.slavesID[slaveId]
            l.info(" Slave [" + itm['hostname'] + " ID=" + itm['id'] +
                   "  CPU = " + str(itm['used_resources']['cpus']) + '/' + str(itm['unreserved_resources']['cpus']))

    def get_slave_cnt(self):
        return self.noOfSlaves

    def get_id(self, id):
        return self.slavesID[id]

    def get_hn(self, hn):
        return self.slavesHN[hn]

    def get_ip_from_pid(self, pid):
        return pid.split('@')[1].split(':')[0]

    def get_slave_ip_from_id(self, slave_id):
        pid = self.slavesID[slave_id]['pid']
        return self.get_ip_from_pid(pid)

    def get_slave_ip_from_hn(self, slave_hn):
        pid = self.slavesHN[slave_hn]['pid']
        return self.get_ip_from_pid(pid)

    def get_slave_ips_from_attribute(self, attr_type, attr_value):
        ret = []
        for host_ip, info in self.slavesHN.items():
            if info["attributes"][attr_type] == attr_value:
                ret.append(host_ip)
        return ret
