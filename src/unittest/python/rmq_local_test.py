__author__ = 'AbdullahS'
from sys import path
path.append("src/main/python")

import unittest
import math
import random
import logging
import os
from pprint import pprint, pformat  # NOQA
from hydra.lib import util
from hydra.rmqtest.runtest import RunTestRMQ

l = util.createlogger('RMQLocalTest', logging.INFO)

class RMQLocalTest(unittest.TestCase):
    def setUp(self):
        l.info("RMQLocalTest initated")

    def test1(self):
        l.info("test1 launched")
        pwd = os.getcwd()
        l.info("CWD = " + pformat(pwd))

        def options():
            None
        setattr(options, 'test_duration', 5)
        setattr(options, 'msg_batch', 50)
        setattr(options, 'msg_rate', 1000)
        setattr(options, 'msg_rate', 1)
        setattr(options, 'total_sub_apps', 1)
        setattr(options, 'config_file', pwd + '/hydra.ini')
        r = RunTestRMQ(options, False)
        r.start_appserver()
        res = r.run_test()
        raw_input("delete all ")
        r.delete_all_launched_apps()
        raw_input("deleted all")
        r.stop_appserver()
        print("RES = " + pformat(res))

if __name__ == '__main__':
    unittest.main()
