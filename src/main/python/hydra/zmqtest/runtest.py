__author__ = 'sushil'

import os
import sys
from ConfigParser import ConfigParser
from pprint import pprint, pformat  # NOQA
from marathon.models import MarathonApp, MarathonConstraint
import time
import logging
from hydra.lib import util
from hydra.lib.runtestbase import RunTestBase


l = util.createlogger('runTest', logging.INFO)
# l.setLevel(logging.DEBUG)


class RunTest(RunTestBase):
    def __init__(self, argv):
        config = ConfigParser()
        config_fn = 'hydra.ini'
        if len(argv) >= 2:
            config_fn = argv[1]
            del argv[1]
        if not os.path.isfile(config_fn):
            l.error("Unable to open config file %s" % config_fn)
            sys.exit(1)
        config.read(config_fn)
        RunTestBase.__init__(self, 'zmqScale', config)

        zstpub = '/zst-pub'
        zstsub = '/zst-sub'
        self.add_appid(zstpub)
        self.add_appid(zstsub)
        self.start_init()
        l.info("Launching the pub app")
        l.info(self.get_cmd('hydra.zmqtest.zmqtests.zmq_pub', '1555'))
        raw_input("====")
        sys.exit(1)
        self.mt.create_app(zstpub,
                          MarathonApp(cmd=self.get_cmd('hydra.zmqtest.zmqtests.zmq_pub', '1555'),
                                      cpus=0.01, mem=32,
                                      constraints=[MarathonConstraint(field='hostname', operator='UNIQUE')],
                                      uris=[self.get_app_uri()]))

        # wait for the application to be launched and be ready and find it's IP
        taskip = self.find_ip_uniqueapp(zstpub)

        # now we can launch subscribe app with ip port
        self.mt.create_app(zstsub,
                          MarathonApp(cmd=self.get_cmd('hydra.zmqtest.zmqtests.zmq_sub', '%s 1555' % taskip),
                                      cpus=0.01, mem=32,
                                      uris=[self.get_app_uri()]))

        a2 = self.mt.wait_app_ready(zstsub, 1)
        l.info("Done with launching the pub and sub processes, will scale the sub side now")
        scale = 100
        self.mt.scale_app(zstsub, scale)
        l.info('Done with starting of scaling the app to %d' % scale)

        cnt = 0
        while True:
            a2 = self.mt.get_app(zstsub)
            l.info('[%d] Application count running = %d, staged = %d' % (cnt, a2.tasks_running, a2.tasks_staged))
            if (a2.tasks_running >= scale):
                break
            cnt += 1
            sys.stdout.flush()
            time.sleep(1)
        l.info("All the tasks are running now. press Ctrl-C to exit. ")
        l.info("  (This app needs to be running to allow scale-up of marathon jobs)")
        self.wait_for_interrupt()
        # l.info("Exiting")
        # self.myserver.stop()
        # self.myserver.join()
