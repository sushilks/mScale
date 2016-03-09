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
   - For now, just dumps the message count received by each client on screen



*To run*:
Modify hydra/hydra.ini   with your mesos, marathon credentials


*Run command*:
pip uninstall -y hydra && pyb install && hydra zmq


*RESULTS*:
Example results:
iINFO 2016-03-09 04:35:36,383 runtest.py:run_test:60 Client: 7f657784de20
INFO 2016-03-09 04:35:36,383 runtest.py:run_test:61 Info: {u'msg_count': 10000}
INFO 2016-03-09 04:35:36,383 runtest.py:run_test:60 Client: 7fb1587eee20
INFO 2016-03-09 04:35:36,383 runtest.py:run_test:61 Info: {u'msg_count': 10000}
INFO 2016-03-09 04:35:36,383 runtest.py:run_test:60 Client: 7f78e19ece20
INFO 2016-03-09 04:35:36,383 runtest.py:run_test:61 Info: {u'msg_count': 10000}
INFO 2016-03-09 04:35:36,383 runtest.py:run_test:60 Client: 7f60a024de20
INFO 2016-03-09 04:35:36,383 runtest.py:run_test:61 Info: {u'msg_count': 10000}
