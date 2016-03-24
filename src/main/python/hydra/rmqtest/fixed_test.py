__author__ = 'AbdullahS'

from pprint import pprint, pformat  # NOQA
import logging
import os
import sys
from datetime import datetime
from hydra.lib import util
#from hydra.zmqtest.runtest import RunTestZMQ
from hydra.rmqtest.runtest import RunTestRMQ
from hydra.lib.boundary import Scanner

l = util.createlogger('runTestSuit', logging.INFO)
# l.setLevel(logging.DEBUG)


class RunSuitFixed(object):
    def __init__(self, argv):
        l.info(" Starting Max Rate ....")
        pwd = os.getcwd()
        fname = 'rmqsuit.test.log'
        ofile = open(pwd + '/' + fname, 'w')
        ofile.truncate()
        ofile.write('Starting at :' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n')
        # def options = lambda: None  # NOQA

        def options():
            None
        setattr(options, 'test_duration', 30)
        setattr(options, 'msg_batch', 50)
        setattr(options, 'msg_rate', 10000)
        setattr(options, 'total_sub_apps', 30)
        setattr(options, 'config_file', pwd + '/hydra.ini')
        setattr(options, 'keep_running', False)
        self.first_test = None
        # Parameters
        # client_set = [5, 10, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
        client_set = [10]
        # client_set = [5, 10, 50, 100, 200, 400]

        for client_count in client_set:
            setattr(options, 'total_sub_apps', int(client_count / 10))
            if not self.first_test:
                runner = RunTestRMQ(options, None)
                self.first_test = runner
                self.first_test.start_appserver()
            else:
                runner = RunTestRMQ(options, None)

            scanner = Scanner(runner.run, 500, 50)
            #res = scanner.range(range(20000, 32000, 1000))
            res = scanner.range(range(10000, 20000, 2000))
            l.info("Found for Client Count %d :" % client_count)
            l.info(" :: " + pformat(res))
            runner.delete_all_launched_apps()
        self.first_test.stop_appserver()
        l.info("TestSuite Compleated.")
        sys.exit(0)


def run(argv):  # NOQA
    RunSuitFixed(argv)
    return True
