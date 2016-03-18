__author__ = 'sushil'

from pprint import pprint, pformat  # NOQA
import logging
import os
import sys
from datetime import datetime
from hydra.lib import util
from hydra.zmqtest.runtest import RunTestZMQ
from hydra.lib.boundary import Scanner

l = util.createlogger('runTestSuit', logging.INFO)
# l.setLevel(logging.DEBUG)


class TestRunner:
    def __init__(self, options, first_run=None):
        self.options = options
        self.first_run = first_run
        self.r = RunTestZMQ(self.options, False)
        self.run_results = {}

    def run(self, message_rate):
        l.info("Starting run with message rate = %d and client count=%d" % (message_rate, self.options.total_sub_apps))
        if message_rate in self.run_results:
            res = self.run_results[message_rate]
        else:
            setattr(self.options, 'msg_rate', message_rate)
            if not self.first_run:
                res = self.r.run_test(False)
                self.first_run = True
            else:
                # Update existing PUB and SUBs instead of launching new
                def options():
                    None
                setattr(options, 'test_duration', 15)
                setattr(options, 'msg_batch', 1000)
                setattr(options, 'msg_rate', message_rate)
                res = self.r.update_metrics_run_test(options)
            self.run_results[message_rate] = res
        l.info("Completed run with message rate = %d and client count=%d " %
               (message_rate, self.options.total_sub_apps) +
               "Reported Rate ; %f and Reported Drop Percentage : %f" %
               (res['average_rate'], res['average_packet_loss']))
        run_pass = True
        if (res['average_tx_rate'] < 0.7 * message_rate):
            # if we are unable to get 70% of the tx rate
            run_pass = False
        return (run_pass, res['average_tx_rate'], res['average_packet_loss'])

    def stop(self):
        if self.first_test:
            self.first_test.stop_appserver()
            self.first_test = None


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
        setattr(options, 'test_duration', 10)
        setattr(options, 'msg_batch', 1000)
        setattr(options, 'msg_rate', 10000)
        setattr(options, 'config_file', pwd + '/hydra.ini')
        setattr(options, 'keep_running', False)

        # Parameters
        # client_set = [10, 20]
        client_set = [10, 20, 40, 80, 160, 500, 1000, 2000, 4000, 8000]
        self.first_test = None
        for client_count in client_set:
            setattr(options, 'total_sub_apps', int(client_count / 10))
            if not self.first_test:
                runner = TestRunner(options, None)
                self.first_test = runner
                self.first_test.r.start_appserver()
            else:
                runner = TestRunner(options, None)
            if client_count < 100:
                scanner = Scanner(runner.run, 10000, 50)
            else:
                scanner = Scanner(runner.run, 500, 50)
            (status, rate, drop) = scanner.find_max_rate()
            l.info("Found for Client Count %d Max message Rate %d with drop %f" %
                   (client_count, rate, drop))
            # Delete all launched apps once the required drop is achieved for this set
            runner.r.delete_all_launched_apps()
        self.first_test.r.stop_appserver()
        l.info("TestSuite Compleated.")
        sys.exit(0)


class RunSuitPacketDrop(object):
    def __init__(self, argv):
        l.info(" Starting ....")
        pwd = os.getcwd()
        fname = 'zmqsuit.test.log'
        ofile = open(pwd + '/' + fname, 'w')
        ofile.truncate()
        ofile.write('Starting at :' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n')
        # def options = lambda: None  # NOQA

        def options():
            None
        setattr(options, 'test_duration', 10)
        setattr(options, 'msg_batch', 1000)
        setattr(options, 'msg_rate', 10000)
        setattr(options, 'config_file', pwd + '/hydra.ini')
        setattr(options, 'keep_running', False)

        # drop_percentage_set = [0, 5, 10, 20]
        # client_set = [10, 20]
        client_set = [10, 20, 40, 80, 160, 500, 1000, 2000, 4000, 8000]
        drop_percentage_set = [0, 10]
        self.first_test = None
        for client_count in client_set:
            setattr(options, 'total_sub_apps', int(client_count / 10))
            if not self.first_test:
                runner = TestRunner(options, None)
                self.first_test = runner
                self.first_test.r.start_appserver()
            else:
                runner = TestRunner(options, None)
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
            runner.r.delete_all_launched_apps()
        self.first_test.r.stop_appserver()
        l.info("TestSuite Compleated.")
        sys.exit(0)


def RunSuit(argv):  # NOQA
    return RunSuitMaxRate(argv)
    # return RunSuitPacketDrop(argv)
