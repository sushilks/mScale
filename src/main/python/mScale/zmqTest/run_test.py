__author__ = 'sushil'

import os
import sys
from ConfigParser import ConfigParser
from pprint import pprint, pformat  # NOQA
from marathon.models import MarathonApp, MarathonConstraint
import netifaces
import time
import logging
from mScale.lib import testAppServer, mmAPI, util, runTestBase


l = util.createLogger('runTest', logging.INFO)
# l.setLevel(logging.DEBUG)


class RunTest(runTestBase.RunTestBase):
    def __init__(self, argv):
        config = ConfigParser()
        configFileName = 'mscale.ini'
        if len(argv) >= 2:
            configFileName = argv[1]
            del argv[1]
        if not os.path.isfile(configFileName):
            l.error("Unable to open config file %s" % configFileName)
            sys.exit(1)
        config.read(configFileName)
        runTestBase.RunTestBase.__init__(self, 'zmqScale', config)

        zstPub = '/zst-pub'
        zstSub = '/zst-sub'
        self.addAppID(zstPub)
        self.addAppID(zstSub)
        self.startInit()
        l.info("Launching the pub app")
        self.mt.createApp(zstPub,
                 MarathonApp(cmd=self.getCmd('mScale.zmqTest.zmq_pub_sub.zmq_pub', '1555'),
                             cpus=0.01,
                             mem=32,
                             constraints=[MarathonConstraint(field='hostname', operator='UNIQUE')],
                             uris=[self.getAppURI()]))

        # wait for the application to be launched and be ready and find it's IP
        taskIP = self.findIPforUniqueAPP(zstPub)

        # now we can launch subscribe app with ip port
        self.mt.createApp(zstSub,
                 MarathonApp(cmd=self.getCmd('mScale.zmqTest.zmq_pub_sub.zmq_sub', '%s 1555' % taskIP),
                             cpus=0.01,
                             mem=32,
                             uris=[self.getAppURI()]))

        a2 = self.mt.waitForAppReady(zstSub, 1)
        l.info("Done with launching the pub and sub processes, will scale the sub side now")
        scale = 100
        self.mt.scaleApp(zstSub, scale)
        l.info('Done with starting of scaling the app to %d' % scale)

        cnt = 0
        while True:
            a2 = self.mt.getApp(zstSub)
            l.info('[%d] Application count running = %d, staged = %d' % (cnt, a2.tasks_running, a2.tasks_staged))
            if (a2.tasks_running >= scale):
                break
            cnt += 1
            sys.stdout.flush()
            time.sleep(1)
        l.info("All the tasks are running now. press Ctrl-C to exit. ")
        l.info("  (This app needs to be running to allow scale-up of marathon jobs)")
        self.waitForInterrupt()
        # l.info("Exiting")
        # self.myserver.stop()
        # self.myserver.join()


