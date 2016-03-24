__author__ = 'sushil'

from pprint import pprint, pformat  # NOQA
import logging
import os
import sys
from datetime import datetime
from hydra.lib import util
from hydra.zmqtest.runtest import RunTestZMQ
from hydra.lib.boundary import Scanner

l = util.createlogger('runSuitMaxRate', logging.INFO)
# l.setLevel(logging.DEBUG)


class RunSuitMaxRate(object):
    def __init__(self, argv):
        l.info(" Starting Max Rate ....")
        pwd = os.getcwd()
        fname = 'zmqsuit.test.log'
        ofile = open(pwd + '/' + fname, 'w')
        ofile.truncate()
        ofile.write('Starting at :' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n')
        # def options = lambda: None  # NOQA

        def options():
            None
        setattr(options, 'test_duration', 15)
        setattr(options, 'msg_batch', 100)
        setattr(options, 'msg_rate', 10000)
        setattr(options, 'config_file', pwd + '/hydra.ini')
        setattr(options, 'keep_running', False)
        self.first_test = None

        # Parameters
        # client_set = [10, 20]
        # client_set = [10, 20, 40, 80, 160, 500, 1000, 2000, 4000, 8000]
        # client_set = [5, 10, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
        # client_set = [10, 20, 40, 80, 160, 500, 1000, 2000, 4000, 8000]
        client_set = [40, 60, 80, 100, 120, 140, 160, 180, 200]

        for client_count in client_set:
            setattr(options, 'total_sub_apps', int(client_count / 10))
            if not self.first_test:
                runner = RunTestZMQ(options, None)
                self.first_test = runner
                self.first_test.start_appserver()
            else:
                runner = RunTestZMQ(options, None)

            if client_count < 100:
                scanner = Scanner(runner.run, 10000)
            else:
                scanner = Scanner(runner.run, 500)
            (status, rate, drop) = scanner.find_max_rate()
            l.info("Found for Client Count %d Max message Rate %d with drop %f" %
                   (client_count, rate, drop))
            if drop != 0:
                l.info("Searching for no-drop rate")
                scanner_drop = Scanner(runner.run, rate / 2)
                (status, step_cnt, drop, rate) = scanner_drop.search(0.001, 0.001)
                l.info("Found for Client Count %d Max message Rate %d with no drop (%f)" %
                       (client_count, rate, drop))

            # Delete all launched apps once the required drop is achieved for this set
            runner.delete_all_launched_apps()
        self.first_test.stop_appserver()
        l.info("TestSuite Compleated.")
        sys.exit(0)


def Run(argv):  # NOQA
    RunSuitMaxRate(argv)
    return True
