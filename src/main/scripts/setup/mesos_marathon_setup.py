# Zookeeper to keep track of the current leader of the master servers.
# The Mesos layer, built on top of this, will provide distributed synchronization and resource handling.
# It is responsible for managing the cluster.
# Marathon, the cluster's distributed init system, is used to schedule tasks and hand work to the slave servers.

import os
import argparse
import setup_helpers
from shell_command import shell_call
import ntpath

parser = argparse.ArgumentParser(description='Mesos Marathon setup script')
# 'default=3' fulfills the Apache Mesos recommendation of having at least three masters for a production environment.
parser.add_argument('--num_masters', '-m', type=int, default=1, help='number of master nodes')
parser.add_argument('--num_slaves', '-s', type=int, default=1, help='number of slave nodes')
parser.add_argument('--start', '-r', type=int, default=1, help='start step')
parser.add_argument('--end', '-e', type=int, default=12, help='end step')
parser.add_argument('--clean', '-c', action='store_true', help='cleanup instances')
args = parser.parse_args()

num_masters=args.num_masters
num_slaves=args.num_slaves

def setup(step):
  if step == 1:
    print("Spawn %d ubuntu 14.04 master servers" % num_masters)
    for i in range(num_masters):
      cmd="aurora spawn master" + str(i) + " ubuntu-14-04 n1-standard-4 1"
      shell_call(cmd)

    print("Spawn %d ubuntu 14.04 slave servers" % num_masters)
    for i in range(num_slaves):
      cmd="aurora spawn slave" + str(i) + " ubuntu-14-04 n1-standard-4 1"
      shell_call(cmd)

  elif step == 2:
    print "Write mesos masters ips in ~/mesos_masters_ips files"
    master_ips = setup_helpers.get_master_instances_ips()
    f = open(os.environ['HOME'] + '/mesos_all_ips', 'w')
    fm = open(os.environ['HOME'] + '/mesos_masters_ips', 'w')
    for ip in master_ips:
      f.write(ip+"\n")
      fm.write(ip+"\n")

    print "Write mesos slaves ips in ~/mesos_slaves_ips files"
    slaves_ips = setup_helpers.get_slave_instances_ips()
    fs = open(os.environ['HOME'] + '/mesos_slaves_ips', 'w')
    for ip in slaves_ips:
      f.write(ip+"\n")
      fs.write(ip+"\n")
    fm.close
    fs.close()
    f.close()

  elif step == 3:
    print "add the Mesosphere repository to resources list of ALL servers"
    script_path_name = setup_helpers.create_add_mesosphere_repo_script()
    script_name=ntpath.basename(script_path_name)
    f = open(os.environ['HOME'] + '/mesos_all_ips', 'r')
    for ip in f:
      ip = ip.rstrip()
      setup_helpers.upload_file(ip, script_path_name)
      setup_helpers.run_cmd_gci(ip, "/bin/bash /home/plumgrid/" + script_name)
      #setup_helpers.run_cmd_gci(ip, "rm /home/plumgrid/" + script_name)
    f.close()
    shell_call("rm " + script_path_name)

  elif step == 4:
    print "update your local package cache to gain access to the new component"
    f = open(os.environ['HOME'] + '/mesos_all_ips', 'r')
    for ip in f:
      ip = ip.rstrip()
      setup_helpers.run_cmd_gci(ip, "sudo apt-get -y update")
    f.close

  elif step == 5:
    print "Installing Jave Runtime Headless environment"
    script_path_name = setup_helpers.create_jave_runtime_headless_install_script()
    script_name=ntpath.basename(script_path_name)
    f = open(os.environ['HOME'] + '/mesos_all_ips', 'r')
    for ip in f:
      ip = ip.rstrip()
      setup_helpers.upload_file(ip, script_path_name)
      setup_helpers.run_cmd_gci(ip, "/bin/bash /home/plumgrid/" + script_name)
      setup_helpers.run_cmd_gci(ip, "rm /home/plumgrid/" + script_name)
    f.close()
    shell_call("rm " + script_path_name)

  elif step == 6:
    # This includes the zookeeper, mesos, marathon, and chronos applications.
    print "On master hosts, install mesos and marathon package"
    f = open(os.environ['HOME'] + '/mesos_masters_ips', 'r')
    for ip in f:
      ip = ip.rstrip()
      setup_helpers.run_cmd_gci(ip, "sudo apt-get install -y mesos marathon")
    f.close

    # For your slave hosts, you only need the mesos package, which also pulls in zookeeper as a dependency:
    print "On slave hosts, install mesos package"
    f = open(os.environ['HOME'] + '/mesos_slaves_ips', 'r')
    for ip in f:
      ip = ip.rstrip()
      setup_helpers.run_cmd_gci(ip, "sudo apt-get -y install mesos")
    f.close

  elif step == 7:
    f = open(os.environ['HOME'] + '/mesos_masters_ips', 'r')
    i = 1
    for ip in f:
      ip = ip.strip()
      # On master servers, we will need to do some additional zookeeper configuration.
      # The first step is to define a unique ID number, from 1 to 255, for each of your master servers. This is kept in the /etc/zookeeper/conf/myid file.
      cmd1 = "\"sudo bash -c 'echo " + str(i) + " > /etc/zookeeper/conf/myid'\""
      # we'll specify the hostname and IP address for each of our master servers. We will be using the IP address for
      # the hostname so that our instances will not have trouble resolving correctly
      cmd2 = "\"sudo bash -c 'echo " + ip + " > /etc/mesos-master/ip' \""
      cmd3 = "\"echo " + ip + " | sudo tee /etc/mesos-master/hostname \""
      setup_helpers.run_cmd_gci(ip, cmd1)
      setup_helpers.run_cmd_gci(ip, cmd2)
      setup_helpers.run_cmd_gci(ip, cmd3)
      i += 1
    f.close

  elif step == 8:
    # we need to modify our zookeeper configuration file to map our zookeeper IDs to actual hosts. This will ensure
    # that the service can correctly resolve each host from the ID system that it uses.
    config = ""
    f = open(os.environ['HOME'] + '/mesos_masters_ips', 'r')
    i = 1
    for ip in f:
      ip = ip.rstrip()
      config += "server." + str(i) + "=" + ip + ":2888:3888\n"
      i += 1
    f.close()
    print config

    script_path_name = setup_helpers.create_zk_conf_script(config)
    script_name=ntpath.basename(script_path_name)
    f = open(os.environ['HOME'] + '/mesos_masters_ips', 'r')
    for ip in f:
      ip = ip.rstrip()
      setup_helpers.upload_file(ip, script_path_name)
      setup_helpers.run_cmd_gci(ip, "/bin/bash /home/plumgrid/" + script_name)
      #setup_helpers.run_cmd_gci(ip, "rm /home/plumgrid/" + script_name)
    f.close()
    shell_call("rm " + script_path_name)

  elif step == 9:
    # configure our zookeeper connection info. This is the underlying layer that allows all of our hosts to connect to the correct master servers.
    print "configure zookeepr connection info"
    config = "zk://"
    f = open(os.environ['HOME'] + '/mesos_masters_ips', 'r')
    for ip in f:
      ip = ip.rstrip()
      config += ip + ":2181,"

    config = config[:-1] + "/mesos"
    f.close

    f = open(os.environ['HOME'] + '/mesos_all_ips', 'r')
    for ip in f:
      ip = ip.strip()
      cmd1 = "sudo service zookeeper restart"
      cmd2 = "\"sudo bash -c 'echo \"" + config + "\" > /etc/mesos/zk'\""
      cmd3 = "\"sudo bash -c 'echo 1 > /etc/mesos-master/quorum' \""
      setup_helpers.run_cmd_gci(ip, cmd1)
      setup_helpers.run_cmd_gci(ip, cmd2)
      setup_helpers.run_cmd_gci(ip, cmd3)
    f.close

  elif step == 10:
    # Configure Marathon
    print "configure zookeepr connection info"
    config = "zk://"
    f = open(os.environ['HOME'] + '/mesos_masters_ips', 'r')
    for ip in f:
      ip = ip.rstrip()
      config += ip + ":2181,"
    config = config[:-1] + "/marathon"
    f.close

    script_path_name = setup_helpers.create_marathon_conf_script(config)
    script_name=ntpath.basename(script_path_name)
    f = open(os.environ['HOME'] + '/mesos_masters_ips', 'r')
    for ip in f:
      ip = ip.rstrip()
      setup_helpers.upload_file(ip, script_path_name)
      setup_helpers.run_cmd_gci(ip, "/bin/bash /home/plumgrid/" + script_name)
      #setup_helpers.run_cmd_gci(ip, "rm /home/plumgrid/" + script_name)
    f.close()
    #shell_call("rm " + script_path_name)

if args.clean:
  shell_call("aurora rm instances master*")
  shell_call("aurora rm instances slave*")
else:
  for step in range(args.start, args.end+1):
    print ("******************* starting step %d ***********************" % step)
    setup(step)

