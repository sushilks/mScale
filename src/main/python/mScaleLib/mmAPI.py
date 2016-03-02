__author__ = 'sushil'

from marathon import MarathonClient
from pprint import pprint, pformat   # NOQA
from mScaleLib import util
import marathon
import requests
import json
import time
import sys
import logging

l = util.createLogger('DSAPI', logging.INFO)
# l.setLevel(logging.DEBUG)


class MarathonIF(object):
    def __init__(self, marathon_addr, my_addr, mesos):
        self.mcli = MarathonClient(marathon_addr)
        self.myAddr = my_addr
        self.mesos = mesos

    def getApps(self):
        listApps = self.mcli.list_apps()
        return listApps

    def getApp(self, app_id):
        try:
            a = self.mcli.get_app(app_id)
        except marathon.exceptions.NotFoundError as e:  # NOQA
            return None
        return a

    def deleteApp(self, app_id, force=False):
        return self.mcli.delete_app(app_id, force)

    def deleteAppIfExisting(self, app_id):
        for idx in range(0, 4):
            try:
                a = self.getApp(app_id)
                if a:
                    return self.deleteApp(app_id, True)
                return None
            except:
                e = sys.exc_info()[0]
                pprint("<p>Error: %s</p>" % e)
        raise

    def createApp(self, app_id, attr):
        for idx in range(0, 10):
            try:
                a = self.mcli.create_app(app_id, attr)
                return a
            except marathon.exceptions.MarathonHttpError as e:
                if str(e).find('App is locked by one or more deployments. Override with the option') > 0:
                    time.sleep(1)
                else:
                    raise
        raise

    def waitForAppRemoval(self, app):
        cnt = 0
        while True:
            if not self.getApp(app):
                break
            time.sleep(0.2)
            cnt += 1
            if cnt > 0:
                l.info("Stuck waiting for %s to be deleted CNT=%d" % (app, cnt))
        return True

    def waitForAppReady(self, app, running_count):
        cnt = 0
        while True:
            a1 = self.getApp(app)
            if a1.tasks_running == running_count:
                return a1
            cnt += 1
            time.sleep(1)
            l.info("[%d]Waiting for task to move to running stage, " % cnt +
                   "current stat staged=%d running=%d expected Running=%d" %
                   (a1.tasks_staged, a1.tasks_running, running_count))

    def scaleApp(self, app, scale):
        return self.mcli.scale_app(app, scale)


class MesosIF(object):
    def __init__(self, addr):
        r = requests.get(addr + '/master/slaves')
        assert r.status_code == 200
        dt = json.loads(r.content)
        self.noOfSlaves = len(dt['slaves'])
        pprint(" Slaves Found : " + str(self.noOfSlaves))
        self.slavesID = {}
        self.slavesHN = {}
        for idx in range(0, self.noOfSlaves):
            itm = dt['slaves'][idx]
            l.info(" Slave [" + itm['hostname'] + " ID=" + itm['id'] +
                   "  CPU = " + str(itm['used_resources']['cpus']) + '/' + str(itm['unreserved_resources']['cpus']))
            self.slavesHN[itm['hostname']] = itm
            self.slavesID[itm['id']] = itm

    def getID(self, id):
        return self.slavesID[id]

    def getHN(self, hn):
        return self.slavesHN[hn]

    def getIPfromPID(self, pid):
        return pid.split('@')[1].split(':')[0]

    def getSlaveIPFromID(self, slave_id):
        pid = self.slavesID[slave_id]['pid']
        return self.getIPfromPID(pid)

    def getSlaveIPFromHN(self, slave_hn):
        pid = self.slavesHN[slave_hn]['pid']
        return self.getIPfromPID(pid)
