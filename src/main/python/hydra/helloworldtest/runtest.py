from hydra.lib.runtestbase import RunTestBase
from optparse import OptionParser


class HW(RunTestBase):
    def __init__(self):
        self.hw_server_app_id = "hw_server"
        self.hw_client_app_id = "hw_client"
        self.hw_server_task_ip = None
        self.hw_server_task_port = None
        self.hw_client_task_ip = None
        self.hw_client_task_port = None
        RunTestBase.__init__(self, 'HelloWorld', None, None, startappserver=True, mock=False)

    def run_test(self):
        # Get Mesos/Marathon client
        super(HW, self).start_init()
        # Launch zmq pub
        self.launch_hw_server()
        # Launch zmq sub up to self.total_sub_apps
        self.launch_hw_client()

    def launch_hw_server(self):
        print ("Launching the HelloWorld server app")
        constraints = [self.app_constraints(field='hostname', operator='UNIQUE')]

        # Use cluster0 for launching the hw_server
        if 0 in self.mesos_cluster:
            # field: slave_id, operator: CLUSTER, value: slave-set1_0
            constraints.append(self.app_constraints(field=self.mesos_cluster[0]['cat'],
                                                    operator='CLUSTER', value=self.mesos_cluster[0]['match']))
        self.create_hydra_app(name=self.hw_server_app_id, app_path='hydra.helloworld.hw_server.run',
                              app_args=None,
                              cpus=0.01, mem=32,
                              ports=[0],
                              constraints=constraints)

        ipm = super(HW, self).get_app_ipport_map(self.hw_server_app_id)
        assert (len(ipm) == 1)

        # Get IP port of launched task of hw_server.
        tasks = self.get_app_tasks(self.hw_server_app_id)
        task_id = tasks[0].taskid
        info = ipm[task_id]
        self.hw_server_task_ip = info[1]
        self.hw_server_task_port = info[0]


    def launch_hw_client(self):
        print ("Launching the sub app")
        constraints = []
        # Use cluster 1 for launching the SUB
        if 1 in self.mesos_cluster:
            constraints.append(self.app_constraints(field=self.mesos_cluster[1]['cat'],
                                                    operator='CLUSTER', value=self.mesos_cluster[1]['match']))
        self.create_hydra_app(name=self.rmqsub, app_path='hydra.helloworld.hw_client.run',
                              app_args='%s' % (self.pub_ip),
                              cpus=0.01, mem=32,
                              ports=[0],
                              constraints=constraints)
        self.scale_sub_app()


class RunTest(object):
    def __init__(self, argv):
        r = HW()
        r.start_appserver()

        res = r.run_test()
        r.delete_all_launched_apps()
        print("RES = " + pformat(res))
        if not options.keep_running:
            r.stop_appserver()
        else:
            print("Keep running is set: Leaving the app server running")
            print("   you can use the marathon gui/cli to scale the app up.")
            print("   after you are done press enter on this window")
            input('>')
            r.stop_appserver()