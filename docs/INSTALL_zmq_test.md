===============================================================================
Hydra zmq scale test
===============================================================================

*Higher level workflow*
- hydra/zmqtest/runtest.py   is the master
   - connects to Mesos, marathon
   - Launches a PUB, x number of SUBs
   - PUB and SUBs have a ZMQ REP server to listen to signals and for data querying etc
   - PUB, SUB config under hydra/src/main/python/hydra/zmqtest/zmq_config.py
   - Once all PUB, SUBs are launched
   - Master signals PUB to send all data
   - Client store the the received data in HDaemon class hydra/src/main/python/hydra/lib/hdaemon.py
   - Master uses  hydra/src/main/python/hydra/lib/h_analyser.py to collect all info
   - For now, just dumps the message count received by each client on screen if its less than expected



*To run*:
Create your hydra.ini with your mesos, marathon credentials


*install*:
pip uninstall -y hydra && pyb install

*Example run command*:
hydra zmq --total_msgs=100000 --msg_batch=100 --msg_delay=0.0001 --total_sub_apps=30 --config_file ~/hydra.ini


*RESULTS*:
Example results:
INFO 2016-03-10 04:34:10,459 runtest.py:run_test:78 Client: 7fc23c8f6e88
INFO 2016-03-10 04:34:10,459 runtest.py:run_test:79 Info: {u'msg_count': 93741}
INFO 2016-03-10 04:34:10,459 runtest.py:run_test:78 Client: 7fec33ad0120
INFO 2016-03-10 04:34:10,459 runtest.py:run_test:79 Info: {u'msg_count': 94126}
INFO 2016-03-10 04:34:10,459 runtest.py:run_test:78 Client: 7f7158825120
INFO 2016-03-10 04:34:10,459 runtest.py:run_test:79 Info: {u'msg_count': 98840}
INFO 2016-03-10 04:34:10,459 runtest.py:run_test:78 Client: 7fab99325120
INFO 2016-03-10 04:34:10,459 runtest.py:run_test:79 Info: {u'msg_count': 95919}
INFO 2016-03-10 04:34:10,459 runtest.py:run_test:82 Total number of clients experiencing packet drop = 30
Calling Server shutdown
Exiting from server
<hydra.zmqtest.runtest.RunTest object at 0x7f287219fdd0>
