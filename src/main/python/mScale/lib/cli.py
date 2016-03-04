"""mscale cli.

Usage:
   mscale cli ls slaves
   mscale cli ls apps
   mscale cli ls task <app>
   mscale cli [force] stop <app>
   mscale cli scale <app> <scale>
   mscale cli (-h | --help)
   mscale cli --version

Options:
   -h --help  Show this screen.
   --version  Show version.
"""
__author__ = 'sushil'

from docopt import docopt
from pprint import pprint, pformat  # NOQA
from ConfigParser import ConfigParser
from mScale.lib import util, mmapi
import os
import sys
import logging

l = util.createlogger('cli', logging.INFO)
# l.setLevel(logging.DEBUG)


def cli(argv):
    config = ConfigParser()
    config_file_name = 'mscale.ini'
    if len(argv) >= 2 and argv[1].find('.ini') != -1:
        config_file_name = argv[1]
        del argv[1]
    if not os.path.isfile(config_file_name):
        l.error("Unable to open config file %s" % config_file_name)
        sys.exit(1)
    config.read(config_file_name)

    mesos_addr = 'http://' + config.get('mesos', 'ip') + ':' + \
                 config.get('mesos', 'port')
    marathon_addr = 'http://' + config.get('marathon', 'ip') + ':' + \
                    config.get('marathon', 'port')

    argv[0] = 'cli'
    args = docopt(__doc__, argv=argv, version='mscale 0.1.0', )
    # pprint (args)
    if args['ls']:
        if args['slaves']:
            mesos = mmapi.MesosIF(mesos_addr)
            mesos.print_slaves()
        elif args['apps']:
            mt = mmapi.MarathonIF(marathon_addr, '127.0.0.1', None)
            apps = mt.get_apps()
            for app in apps:
                st = "App:" + app.id
                st += " CPU:" + str(app.cpus)
                st += " MEM:" + str(app.mem)
                st += " Instances:" + str(app.instances)
                if len(app.constraints):
                    st += " Constraints:" + pformat(app.constraints)
                l.info(st)
        elif args['task']:
            mt = mmapi.MarathonIF(marathon_addr, '127.0.0.1', None)
            app = mt.get_app(args['<app>'])
            st = "App:" + args['<app>']
            st += " CPU:" + str(app.cpus)
            st += " MEM:" + str(app.mem)
            st += " Instances:" + str(app.instances)
            if len(app.constraints):
                st += " Constraints:" + pformat(app.constraints)
            l.info(st)
            st = "CMD:" + app.cmd
            l.info(st)
            st = "ID:" + app.id
            st += " task_running:" + str(app.tasks_running)
            st += " task_staged:" + str(app.tasks_staged)
            l.info(st)
            tasks = app.tasks
            for task in tasks:
                st = "\tTASK ID:" + task.id + " host:" + task.host
                if len(task.ports):
                    st += " ports:" + pformat(task.ports)
                if len(task.service_ports):
                    st += " service_ports:" + pformat(task.service_ports)
                l.info(st)
    elif args['stop']:
        mt = mmapi.MarathonIF(marathon_addr, '127.0.0.1', None)
        l.info("Deleting app:" + args['<app>'])
        mt.delete_app(args['<app>'], args['force'])
        l.info("Waiting for app removal to complete")
        mt.wait_app_removal(args['<app>'])
    elif args['scale']:
        mt = mmapi.MarathonIF(marathon_addr, '127.0.0.1', None)
        app = args['<app>']
        scale = int(args['<scale>'])
        l.info("Scaling app:" + app + " to scale:" + str(scale))
        mt.scale_app(app, scale)
        l.info("Waiting for app scale to complete")
        mt.wait_app_ready(app, scale)
