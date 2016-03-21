__author__ = 'sushil'

from pprint import pprint, pformat  # NOQA
import logging
import os
import sys
from datetime import datetime  # NOQA
from hydra.lib import util
from hydra.zmqtest.runtest import RunTestZMQ
from hydra.lib.boundary import Scanner

l = util.createlogger('runTestSuit', logging.INFO)
# l.setLevel(logging.DEBUG)


class RunSuitPacketDrop(object):
    def __init__(self, argv):
        l.info(" Starting ....")
        pwd = os.getcwd()

        def options():
            None
        setattr(options, 'test_duration', 60)
        setattr(options, 'msg_batch', 1000)
        setattr(options, 'msg_rate', 10000)
        setattr(options, 'config_file', pwd + '/hydra.ini')
        setattr(options, 'keep_running', False)

        # drop_percentage_set = [0, 5, 10, 20]
        # client_set = [10, 20]
        # client_set = [10, 20, 40, 80, 160, 500, 1000, 2000, 4000, 8000]
        # drop_percentage_set = [0, 10]
        self.first_test = None
        # Parameters
        # client_set = [5, 10, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
        # client_set = [20, 40, 60, 80, 100, 120, 140, 160]
        client_set = [160, 180, 200, 220, 240]
        # client_set = [5, 10, 50, 100, 200, 400]
        # drop_percentage_set = [0, 5, 10, 20]
        drop_percentage_set = [0, 5, 10]
        for client_count in client_set:
            setattr(options, 'total_sub_apps', int(client_count / 10))
            if not self.first_test:
                runner = RunTestZMQ(options, None)
                self.first_test = runner
                self.first_test.start_appserver()
            else:
                runner = RunTestZMQ(options, None)
            if client_count < 100:
                scanner = Scanner(runner.run, 10000, 50)
            else:
                scanner = Scanner(runner.run, 500, 50)

            for drop_percentage in drop_percentage_set:
                (status, step_cnt, res) = scanner.search(drop_percentage)
                if status:
                    l.info("Found for Client Count %d DropRate %d Max message Rate %d after %d run's" %
                           (client_count, drop_percentage, res, step_cnt))
                else:
                    l.info("Unable to Find for Client Count %d DropRate %d failed to increase the rate to %d" %
                           (client_count, drop_percentage, res))
                    # If there is a failure to achieve higher rates let's not do more runs with the same client count
                    break
            # Delete all launched apps once the required drop is achieved for this set
            runner.delete_all_launched_apps()
        self.first_test.stop_appserver()
        l.info("TestSuite Compleated.")
        sys.exit(0)


def RunSuit(argv):  # NOQA
    RunSuitPacketDrop()
    return True
