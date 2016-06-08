__author__ = 'annyz'

from pprint import pprint, pformat  # NOQA
import logging
from hydra.lib import util
from hydra.kafkatest.runtest import RunTestKAFKA
import os

l = util.createlogger('batchTest', logging.INFO)


class RunBatchTest(object):
    def __init__(self, argv):
        l.info(" Starting Kafka Batch Size Test")
        pwd = os.getcwd()

        def options():
            None

        setattr(options, 'test_duration', 10)
        setattr(options, 'msg_batch', 1000)
        setattr(options, 'msg_rate', 30000)
        setattr(options, 'config_file', pwd + '/hydra.ini')
        setattr(options, 'keep_running', False)
        setattr(options, 'acks', 1)
        setattr(options, 'linger_ms', 0)
        setattr(options, 'consumer_max_buffer_size', 0)
        first_test = True
        # Parameters
        client_set = [30, 60, 120, 240, 480, 960, 1920]
        msg_batch_set = [100, 200, 500, 1000, 2000, 5000]

        for client_num in client_set:
            setattr(options, 'total_sub_apps', int(client_num / 10))
            for msg_batch in msg_batch_set:
                setattr(options, 'msg_batch', msg_batch)
                if first_test:
                    r = RunTestKAFKA(options, False)
                    r.start_appserver()
                    first_test = False
                else:
                    r.set_options(options)
                    r.scale_sub_app()
                res = r.run_test()
                l.info("Test Results for batch_size: [%s]" % str(msg_batch))
                print("RES = " + pformat(res))
        r.delete_all_launched_apps()
        if not options.keep_running:
            r.stop_appserver()
        else:
            print("Keep running is set: Leaving the app server running")
            print("   you can use the marathon gui/cli to scale the app up.")
            print("   after you are done press enter on this window")
            input('>')
            r.stop_appserver()


def Run(argv):  # NOQA
    RunBatchTest(argv)
    return True
