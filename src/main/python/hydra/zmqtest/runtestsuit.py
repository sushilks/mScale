__author__ = 'sushil'

from pprint import pprint, pformat  # NOQA
import logging
import os
from datetime import datetime
from hydra.lib import util
from hydra.zmqtest.runtest import RunTestZMQ
from hydra.lib.boundary import Scanner

l = util.createlogger('runTestSuit', logging.INFO)
# l.setLevel(logging.DEBUG)


class TestRunner:
    def __init__(self, options, first_test=None):
        self.options = options
        self.first_test = first_test
        self.run_results = {}

    def run(self, message_rate):
        l.info("Starting run with message rate = %d and client count=%d" % (message_rate, self.options.total_sub_apps))
        if message_rate in self.run_results:
            res = self.run_results[message_rate]
        else:
            setattr(self.options, 'msg_rate', message_rate)
            r = RunTestZMQ(self.options, False)
            if not self.first_test:
                self.first_test = r
                self.first_test.start_appserver()
            res = r.run_test(False)
            self.run_results[message_rate] = res
        l.info("Completed run with message rate = %d and client count=%d " %
               (message_rate, self.options.total_sub_apps) +
               "Reported Rate ; %f and Reported Drop Percentage : %f" %
               (res['average_rate'], res['average_packet_loss']))
        run_pass = True
        if (res['average_tx_rate'] < 0.7 * message_rate):
            # if we are unable to get 70% of the tx rate
            run_pass = False
        return (run_pass, res['average_packet_loss'])

    def get_first_test(self):
        # Hack till we can figure out a clean way to shut down appserver
        return self.first_test

    def stop(self):
        if self.first_test:
            self.first_test.stop_appserver()
            self.first_test = None


class RunSuit(object):
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
        setattr(options, 'test_duration', 5)
        setattr(options, 'msg_batch', 1000)
        setattr(options, 'msg_rate', 10000)
        setattr(options, 'total_sub_apps', 30)
        setattr(options, 'config_file', pwd + '/hydra.ini')
        setattr(options, 'keep_running', False)

        # Parameters
        # client_set = [5, 10, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
        client_set = [10, 1000, 2000, 5000, 8000]
        # client_set = [5, 10, 50, 100, 200, 400]
        # drop_percentage_set = [0, 5, 10, 20]
        drop_percentage_set = [0, 10]
        first_test = None
        for client_count in client_set:
            runner = TestRunner(options, first_test)
            if client_count < 50:
                scanner = Scanner(runner.run, 10000, 50)
            else:
                scanner = Scanner(runner.run, 500, 50)
            for drop_percentage in drop_percentage_set:
                setattr(options, 'total_sub_apps', int(client_count / 10))
                (status, step_cnt, res) = scanner.search(drop_percentage)
                if status:
                    l.info("Found for Client Count %d DropRate %d Max message Rate %d after %d run's" %
                           (client_count, drop_percentage, res, step_cnt))
                else:
                    l.info("Unable to Find for Client Count %d DropRate %d failed to increase the rate to %d" %
                           (client_count, drop_percentage, res))
                    # If there is a failure to achieve higher rates let's not do more runs with the same client count
                    break
            first_test = runner.get_first_test()
        first_test.stop_appserver()
        first_test = None
