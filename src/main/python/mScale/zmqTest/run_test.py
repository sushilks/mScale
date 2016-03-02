__author__ = 'sushil'

import os
import sys
from ConfigParser import ConfigParser
from pprint import pprint, pformat  # NOQA
from marathon.models import MarathonApp, MarathonConstraint
import netifaces
import time
import logging
from mScale.lib import testAppServer, mmAPI, util


l = util.createLogger('runTest', logging.INFO)
# l.setLevel(logging.DEBUG)


def RunTest():
    config = ConfigParser()
    if len(sys.argv) == 2:
        config.read(sys.argv[1])
    else:
        config.read('zst.ini')
    myport = config.getint('zst', 'port')
    myserver = testAppServer.TServer(myport, 'live')
    myserver.start()
    mydev = config.get('zst', 'dev')
    myip = netifaces.ifaddresses(mydev)[2][0]['addr']
    myaddr = 'http://' + myip + ':' + str(myport)

    # now init the marathon plugin and create a app for this path
    mesos_addr = 'http://' + config.get('mesos', 'ip') + ':' + \
                 config.get('mesos', 'port')
    marathon_addr = 'http://' + config.get('marathon', 'ip') + ':' + \
                    config.get('marathon', 'port')
    mesos = mmAPI.MesosIF(mesos_addr)
    mt = mmAPI.MarathonIF(marathon_addr, myip, mesos)
    # delete the running application
    l.info("Delete any pre-existing apps")
    mt.deleteAppIfExisting('/zst-pub')
    mt.deleteAppIfExisting('/zst-sub')
    # wait for the application to be removed
    l.info("Waiting for delete to complete")
    mt.waitForAppRemoval('/zst-pub')
    mt.waitForAppRemoval('/zst-sub')
    l.info("Populating the app on the server")
    os.system("rm ../live/zmq_scale_test.tgz")
    os.system("cd .. && tar cfz live/zmq_scale_test.tgz target src build.py")
    l.info("Launching the pub app")
    mt.createApp('/zst-pub',
                 MarathonApp(cmd='chmod +x ./run_test.sh && ./run_test.sh pub 1555',
                             cpus=0.01,
                             mem=32,
                             constraints=[MarathonConstraint(field='hostname', operator='UNIQUE')],
                             uris=[myaddr + '/zmq_scale_test.tgz', myaddr + '/run_test.sh']))

    # wait for the application to be launched and be ready
    a1 = mt.waitForAppReady('/zst-pub', 1)
    taskIP = None
    for task in a1.tasks:
        l.info("TASK " + task.id + " Running on host : " + task.host + ' IP = ' + mesos.getSlaveIPFromHN(task.host))
        taskIP = mesos.getSlaveIPFromHN(task.host)

    # now we can launch subscribe app with ip port
    mt.createApp('/zst-sub',
                 MarathonApp(cmd="chmod +x ./run_test.sh && ./run_test.sh sub %s 1555" % taskIP,
                             cpus=0.01,
                             mem=32,
                             uris=[myaddr + '/zmq_scale_test.tgz', myaddr + '/run_test.sh']))

    a2 = mt.waitForAppReady('/zst-sub', 1)
    l.info("Done with launching the pub and sub processes, will scale the sub side now")
    scale = 100
    mt.scaleApp('/zst-sub', scale)
    l.info('Done with starting of scaling the app to %d' % scale)

    cnt = 0
    while True:
        a2 = mt.getApp('/zst-sub')
        l.info('[%d] Application count running = %d, staged = %d' % (cnt, a2.tasks_running, a2.tasks_staged))
        if (a2.tasks_running >= scale):
            break
        cnt += 1
        sys.stdout.flush()
        time.sleep(1)
    l.info("All the tasks are running now. press Ctrl-C to exit.")

    try:
        while 1:
            sys.stdout.flush()
            time.sleep(1)
    except KeyboardInterrupt:
        l.info("Exiting")
        myserver.stop()
        myserver.join()
    pass
