__author__ = 'AbdullahS'
from sys import path
path.append("src/main/python")

import unittest
import logging
import os
from pprint import pprint, pformat  # NOQA
from hydra.lib import util
from hydra.rmqtest.runtest import RunTestRMQ

l = util.createlogger('RMQLocalTest', logging.INFO)


class RMQLocalTest(unittest.TestCase):
    """
    Test class that runs a full RabbitMQ PUB/SUB
    test locally. The pub and sub processes are
    goverened and launched by a mock backend
    hydra/src/main/python/hydra/lib/mock_backend.py

    The test is given an illusion that its running on
    hydra mesosphere infra.
    """
    def setUp(self):
        l.info("RMQLocalTest initated")

    def test1(self):
        l.info("test1 launched")
        pwd = os.getcwd()
        l.info("CWD = " + pformat(pwd))

        def options():
            None
        setattr(options, 'test_duration', 10)
        setattr(options, 'msg_batch', 50)
        setattr(options, 'msg_rate', 1000)
        setattr(options, 'total_sub_apps', 1)
        # TODO: AbdullahS: see if we can get rid of config file
        #       requirement for local tests
        setattr(options, 'config_file', pwd + '/src/unittest/python/test.ini')
        r = RunTestRMQ(options, runtest=False, mock=True)
        r.start_appserver()
        res = r.run_test()
        r.delete_all_launched_apps()
        r.stop_appserver()
        print("RES = " + pformat(res))

        # Remove unittest process logs from live directory
        files = [f for f in os.listdir("./live") if f.endswith(".log")]
        for f in files:
            try:
                f_name = "./live/" + f
                l.debug("removing %s", f_name)
                os.remove(f_name)
            except:
                pass

if __name__ == '__main__':
    unittest.main()
