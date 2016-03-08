__author__ = 'sushil'

import sys
from pprint import pprint, pformat  # NOQA
import time
import logging
from hydra.lib import util
from hydra.lib.runtestbase import RunTestBase
try:
    # Python 2.x
    from ConfigParser import ConfigParser
except ImportError:
    # Python 3.x
    from configparser import ConfigParser


l = util.createlogger('runTest', logging.INFO)
# l.setLevel(logging.DEBUG)


class RunTest(RunTestBase):
    def __init__(self, argv):
        config = ConfigParser()
        config_fn = 'hydra.ini'
        if len(argv) >= 2:
            config_fn = argv[1]
            del argv[1]
        RunTestBase.__init__(self, 'zmqScale', config, config_fn)

        zstpub = '/zst-pub'
        zstsub = '/zst-sub'
        self.add_appid(zstpub)
        self.add_appid(zstsub)
        self.start_init()
        l.info("Launching the pub app")
        self.create_hydra_app(name=zstpub, app_path='hydra.zmqtest.zmqtests.zmq_pub', app_args='1555',
                              cpus=0.01, mem=32,
                              constraints=[self.app_constraints(field='hostname', operator='UNIQUE')])

        # wait for the application to be launched and be ready and find it's IP
        taskip = self.find_ip_uniqueapp(zstpub)

        # now we can launch subscribe app with ip port
        self.create_hydra_app(name=zstsub,
                              app_path='hydra.zmqtest.zmqtests.zmq_sub', app_args='%s 1555' % taskip,
                              cpus=0.01, mem=32)
        a2 = self.wait_app_ready(zstsub, 1)
        l.info("Done with launching the pub and sub processes, will scale the sub side now")
        scale = 100
        self.scale_app(zstsub, scale)
        l.info('Done with starting of scaling the app to %d' % scale)

        cnt = 0
        while True:
            a2 = self.get_app(zstsub)
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
