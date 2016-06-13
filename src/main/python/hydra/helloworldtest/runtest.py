import time

from hydra.lib.runtestbase import RunTestBase
try:
    # Python 2.x
    from ConfigParser import ConfigParser
except ImportError:
    # Python 3.x
    from configparser import ConfigParser


class HW(RunTestBase):
    def __init__(self):
        self.config = ConfigParser()  # Object contains 'configurations' parsed from hydra.ini config file
        RunTestBase.__init__(self, 'HelloWorld', None, None, startappserver=True, mock=False)
        self.hw_server_app_id = super(HW, self).format_appname("/hw-server")
        self.hw_client_app_id = super(HW, self).format_appname("/hw-client")
        self.hw_server_task_ip = None
        self.hw_server_task_port = None
        self.hw_client_task_ip = None
        self.hw_client_task_port = None
        self.add_appid(self.hw_server_app_id)
        self.add_appid(self.hw_client_app_id)

    def run_test(self):
        # Get Mesos/Marathon client
        super(HW, self).start_init()
        # Launch HelloWorld server
        self.launch_hw_server()
        # Launch HelloWorld client
        self.launch_hw_client()

    def launch_hw_server(self):
        print ("Launching the HelloWorld server app")
        constraints = [self.app_constraints(field='hostname', operator='UNIQUE')]

        # Use cluster0 for launching the hw_server
        if 0 in self.mesos_cluster:
            # field: slave_id, operator: CLUSTER, value: slave-set1_0
            constraints.append(self.app_constraints(field=self.mesos_cluster[0]['cat'],
                                                    operator='CLUSTER', value=self.mesos_cluster[0]['match']))
        self.create_hydra_app(name=self.hw_server_app_id, app_path='hydra.helloworldtest.hw_server.run',
                              app_args=" ",
                              cpus=0.01, mem=32,
                              ports=[0],
                              constraints=constraints)

        ipm = super(HW, self).get_app_ipport_map(self.hw_server_app_id)
        assert (len(ipm) == 1)

        self.hw_server_task_ip = ipm.values()[0][1]
        self.hw_server_task_port = str(ipm.values()[0][0])
        print("[helloworldtest.hw_server] hw_server running at [%s:%s]", self.hw_server_task_ip,
              self.hw_server_task_port)
        # Get IP port of launched task of hw_server.
        # tasks = self.get_app_tasks(self.hw_server_app_id)
        # task_id = tasks[0].taskid
        # info = ipm[task_id]
        # self.hw_server_task_ip = info[1]
        # self.hw_server_task_port = info[0]

    def launch_hw_client(self):
        print ("Launching the HelloWorld client app")
        constraints = []
        # Use cluster 1 for launching the SUB
        if 1 in self.mesos_cluster:
            constraints.append(self.app_constraints(field=self.mesos_cluster[1]['cat'],
                                                    operator='CLUSTER', value=self.mesos_cluster[1]['match']))
        self.create_hydra_app(name=self.hw_client_app_id, app_path='hydra.helloworldtest.hw_client.run',
                              app_args='%s' % (self.hw_server_task_ip),
                              cpus=0.01, mem=32,
                              ports=[0],
                              constraints=constraints)


class RunTest(object):
    def __init__(self, argv):
        r = HW()
        r.start_appserver()
        r.run_test()
        time.sleep(60)
        print ("Going to delete all launched apps")
        r.delete_all_launched_apps()
        r.stop_appserver()
