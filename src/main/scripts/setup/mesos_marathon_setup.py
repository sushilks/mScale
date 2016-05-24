# Zookeeper to keep track of the current leader of the master servers.
# The Mesos layer, built on top of this, will provide distributed synchronization and resource handling.
# It is responsible for managing the cluster.
# Marathon, the cluster's distributed init system, is used to schedule tasks and hand work to the slave servers.

import os
import argparse
import setup_helpers
import ConfigParser
from shell_command import shell_call
import ntpath
from fabric.api import *

parser = argparse.ArgumentParser(description='Mesos Marathon setup script')
# 'default=3' fulfills the Apache Mesos recommendation of having at least three masters for a production environment.
parser.add_argument('--num_masters', '-m', type=int, default=1, help='number of master nodes')
parser.add_argument('--num_slaves', '-s', type=int, default=1, help='number of slave nodes')
parser.add_argument('--config_file', '-f', type=str, default="/home/muneeb/config.ini", help='Setup configuration file')

parser.add_argument('--dst_work_dir', '-w', type=str, default="/home/plumgrid", help='Destination work directory. All contents will be uploaded here.')
parser.add_argument('--dst_user_name', '-u', type=str, default="plumgrid", help='Destination user name')
parser.add_argument('--start', '-r', type=int, default=1, help='start step')
parser.add_argument('--end', '-e', type=int, default=17, help='end step')
parser.add_argument('--clean', '-c', action='store_true', help='cleanup instances')
args = parser.parse_args()

num_masters=args.num_masters
num_slaves=args.num_slaves
config_file=args.config_file
dst_work_dir=args.dst_work_dir
dst_user_name=args.dst_user_name
mesos_all_ips_list = setup_helpers.get_mesos_all_ips()
mesos_masters_ips_list = setup_helpers.get_mesos_masters_ips()
mesos_slaves_ips_list= setup_helpers.get_mesos_slaves_ips()

def setup(step):
  if step == 1:
    # TODO: Write cleanup function and call it here. Remove all ips files.
    config = ConfigParser.ConfigParser()
    config.read(config_file)
    sections = config.sections()
    for section in sections:
      options_dict = setup_helpers.config_section_map(config, section)
      print ("count=%s, tag=%s, type=%s" %(options_dict["tag"], options_dict["count"], options_dict["machinetype"]))
      count = options_dict["count"]
      machinetype = options_dict["machinetype"]
      tag = options_dict["tag"]
      for i in range(int(count)):
        cmd = "aurora spawn " + section + "-" + tag + "-" + str(i) + " ubuntu-14-04 " + machinetype
        shell_call(cmd)

    #print("Spawn %d ubuntu 14.04 master servers" % num_masters)
    #for i in range(num_masters):
    #  cmd="aurora spawn master" + str(i) + " ubuntu-14-04 n1-standard-4"
    #  shell_call(cmd)
      #setup_helpers.spawn_instance("master" + str(i), "ubuntu-14-04")

    #print("Spawn %d ubuntu 14.04 slave servers" % num_masters)
    #for i in range(num_slaves):
    #  cmd="aurora spawn slave" + str(i) + " ubuntu-14-04 n1-standard-4 1"
    #  shell_call(cmd)
      #setup_helpers.spawn_instance("slave" + str(i), "ubuntu-14-04")

  elif step == 2:
    # Purpose of this step is to enable the script to work for physical or other (e.g AWS) deployments.
    # All user has to do is to create a text file holding ips and run script from step 3.
    # TODO: 1. Write first 2 steps as a seperate script and call it as infra_setup(). Infra setup script
    #          may be written for various environments like AZURE, AWS etc.
    #       2. Current script will start from step 3 and will be called mesos_setup().
    #       3. Another script will take infra as argument (GCE, AWS, Azure) and will call appropriate
    #          infra script along with mesos setup.
    print "==> Write mesos masters ips in ~/mesos_masters_ips files"
    master_ips = setup_helpers.get_master_instances_ips()
    f = open(os.environ['HOME'] + '/mesos_all_ips', 'w')
    fm = open(os.environ['HOME'] + '/mesos_masters_ips', 'w')
    for ip in master_ips:
      f.write(ip+"\n")
      fm.write(ip+"\n")

    print "==> Write mesos slaves ips in ~/mesos_slaves_ips files"
    slaves_ips = setup_helpers.get_slave_instances_ips()
    fs = open(os.environ['HOME'] + '/mesos_slaves_ips', 'w')
    for ip in slaves_ips:
      f.write(ip+"\n")
      fs.write(ip+"\n")
    fm.close
    fs.close()
    f.close()

  # ******************************* Install Mesos Sphere on the servers. ********************************
  elif step == 3:
    print "==> Add Mesosphere repository to resources list of ALL hosts"
    script_path_name = os.getcwd() + "/vm_files/add_mesos_sphere_repo.sh"
    script_name=ntpath.basename(script_path_name)

    print ("==> Uploading %s to %s" % (script_path_name, dst_work_dir))
    setup_helpers.upload_to_multiple_hosts(dst_user_name, mesos_all_ips_list, script_path_name, dst_work_dir)

    print ("==> Running %s/%s script" % (dst_work_dir, script_name))
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_all_ips_list, "/bin/bash " + dst_work_dir + "/" + script_name)

  elif step == 4:
    print "==> Installing Jave Runtime Headless environment"
    script_path_name = os.getcwd() + "/vm_files/install_JR_headless_env.sh"
    script_name=ntpath.basename(script_path_name)

    print ("==> Uploading %s to %s" % (script_path_name, dst_work_dir))
    setup_helpers.upload_to_multiple_hosts(dst_user_name, mesos_all_ips_list, script_path_name, dst_work_dir)

    print ("==> Running %s/%s script" % (dst_work_dir, script_name))
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_all_ips_list, "/bin/bash " + dst_work_dir + "/" + script_name)

  elif step == 5:
    # This includes the zookeeper, mesos, marathon, and chronos applications.
    print "==> On master hosts, install mesos and marathon package"
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_masters_ips_list, "sudo apt-get install -y mesos marathon")

    # For your slave hosts, you only need the mesos package, which also pulls in zookeeper as a dependency:
    print "==> On slave hosts, install mesos package"
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_slaves_ips_list, "sudo apt-get -y install mesos")

  elif step == 6:
    # configure our zookeeper connection info. This is the underlying layer that allows all of our hosts to connect to the correct master servers.
    print "==> configure zookeepr connection info"
    config = "zk://"
    f = open(os.environ['HOME'] + '/mesos_masters_ips', 'r')
    for ip in f:
      ip = ip.rstrip()
      config += ip + ":2181,"
    config = config[:-1] + "/mesos"
    f.close

    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_all_ips_list, "echo '" + config + "' > /etc/mesos/zk", use_sudo=True)

  # ******************************* Master Servers' Zookeeper Configuration ********************************
  # On master servers, we will need to do some additional zookeeper configuration.
  # The first step is to define a unique ID number, from 1 to 255, for each of your master servers. This is kept in the /etc/zookeeper/conf/myid file.
  # we'll specify the hostname and IP address for each of our master servers. We will be using the IP address for
  # the hostname so that our instances will not have trouble resolving correctly
  elif step == 7:
    f = open(os.environ['HOME'] + '/mesos_masters_ips', 'r')
    i = 1
    for ip in f:
      ip = ip.strip()
      setup_helpers.run_cmd_on_host(dst_user_name, ip, "echo " + str(i) + " > /etc/zookeeper/conf/myid", use_sudo=True)
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
    script_path_name = setup_helpers.create_zk_conf_script(config)
    script_name=ntpath.basename(script_path_name)

    print ("==> Uploading %s to /etc/zookeeper/conf/" % script_path_name)
    setup_helpers.upload_to_multiple_hosts(dst_user_name, mesos_masters_ips_list, script_path_name, "/etc/zookeeper/conf/", use_sudo=True)

  # ******************************* Master Servers' Mesos Configuration ********************************
  elif step == 9:
    # TODO: Calculate quoram value
    # quoram_num = (num_masters // 2) + 1
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_masters_ips_list, "echo 1 > /etc/mesos-master/quorum", use_sudo=True)

    f = open(os.environ['HOME'] + '/mesos_masters_ips', 'r')
    for ip in f:
      ip = ip.strip()
      setup_helpers.run_cmd_on_host(dst_user_name, ip, "echo " + ip + " > /etc/mesos-master/ip",  use_sudo=True)
      setup_helpers.run_cmd_on_host(dst_user_name, ip, "echo " + ip + " > /etc/mesos-master/hostname",  use_sudo=True)
    f.close

  # ******************************* Master Servers' Marathon Configuration ********************************
  elif step == 10:
    print "==> Configuring Master server's Marathon configuration"
    script_path_name = os.getcwd() + "/vm_files/master_marathon_conf.sh"
    script_name=ntpath.basename(script_path_name)

    print ("==> Uploading %s to %s" % (script_path_name, dst_work_dir))
    setup_helpers.upload_to_multiple_hosts(dst_user_name, mesos_masters_ips_list, script_path_name, dst_work_dir)

    print ("==> Running %s/%s script" % (dst_work_dir, script_name))
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_masters_ips_list, "/bin/bash " + dst_work_dir + "/" + script_name)

  # ******************************* Configure Service Init Rules and Restart Services ********************************
  elif step == 11:
    print "==> Configuring Service init rules and Restart Services"
    script_path_name = os.getcwd() + "/vm_files/srv_init_rules_and_restart_srv.sh"
    script_name=ntpath.basename(script_path_name)

    print ("==> Uploading %s to %s" % (script_path_name, dst_work_dir))
    setup_helpers.upload_to_multiple_hosts(dst_user_name, mesos_masters_ips_list, script_path_name, dst_work_dir)

    print ("==> Running %s/%s script" % (dst_work_dir, script_name))
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_masters_ips_list, "/bin/bash " + dst_work_dir + "/" + script_name)

  # ##################################################################################################################
  #                                           SLAVE NODEs setup
  # ##################################################################################################################
  elif step == 12:
    print "==> Configuring slave nodes"
    f = open(os.environ['HOME'] + '/mesos_slaves_ips', 'r')
    for ip in f:
      ip = ip.rstrip()
      script_path_name = setup_helpers.create_slave_conf_script(ip)
      script_name = ntpath.basename(script_path_name)

      print ("==> Uploading %s to %s" % (script_path_name, dst_work_dir))
      setup_helpers.upload_to_host(dst_user_name, ip, script_path_name, dst_work_dir)

      print ("==> Running %s/%s script" % (dst_work_dir, script_name))
      setup_helpers.run_cmd_on_host(dst_user_name, ip, "/bin/bash " + dst_work_dir + "/" + script_name)
    f.close()

    # ##################################################################################################################
    #                                           Hydra setup
    # ##################################################################################################################
    # TODO: Needs to move to another script.
  elif step == 13:
    print "==> Install protobuf on all nodes"
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_all_ips_list, "wget http://launchpadlibrarian.net/160197953/libprotobuf7_2.4.1-3ubuntu4_amd64.deb")
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_all_ips_list, "dpkg -i ./libprotobuf7_2.4.1-3ubuntu4_amd64.deb", use_sudo=True)

  elif step == 14:
    print "==> Configuring Slaves for Hydra"
    script_path_name = os.getcwd() + "/vm_files/hydra_slave_setup.sh"
    script_name=ntpath.basename(script_path_name)

    print ("==> Uploading %s to %s" % (script_path_name, dst_work_dir))
    setup_helpers.upload_to_multiple_hosts(dst_user_name, mesos_slaves_ips_list, script_path_name, dst_work_dir)

    print ("==> Running %s/%s script" % (dst_work_dir, script_name))
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_slaves_ips_list, "/bin/bash " + dst_work_dir + "/" + script_name)

  elif step == 15:
    print "==> Clone hydra on master node"
    setup_helpers.run_cmd_on_host(dst_user_name, mesos_masters_ips_list[0], "sudo apt-get -y install git unzip python-pip")
    setup_helpers.run_cmd_on_host(dst_user_name, mesos_masters_ips_list[0], "wget https://github.com/sushilks/hydra/archive/master.zip && unzip master.zip")

  elif step == 16:
    print "==> Upload conf file"
    script_path_name = setup_helpers.create_hydra_conf(mesos_masters_ips_list[0])
    script_name = ntpath.basename(script_path_name)

    print ("==> Uploading %s to %s" % (script_path_name, dst_work_dir))
    setup_helpers.upload_to_host(dst_user_name, mesos_masters_ips_list[0], script_path_name, dst_work_dir + "/hydra-master")

  elif step == 17:
    print "==> Install packages for hydra"
    script_path_name = os.getcwd() + "/vm_files/hydra_pkgs_install.sh"
    script_name=ntpath.basename(script_path_name)

    print ("==> Uploading %s to %s" % (script_path_name, dst_work_dir))
    setup_helpers.upload_to_multiple_hosts(dst_user_name, mesos_masters_ips_list, script_path_name, dst_work_dir)

    print ("==> Running %s/%s script" % (dst_work_dir, script_name))
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_masters_ips_list, "/bin/bash " + dst_work_dir + "/" + script_name + " " + dst_work_dir)


if args.clean:
  shell_call("aurora rm instances master*")
  shell_call("aurora rm instances slave*")
  shell_call("rm ~/mesos_all_ips")
  shell_call("rm ~/mesos_masters_ips")
  shell_call("rm ~/mesos_slaves_ips")
else:
  for step in range(args.start, args.end+1):
    print ("******************* starting step %d ***********************" % step)
    mesos_all_ips_list = setup_helpers.get_mesos_all_ips()
    mesos_masters_ips_list = setup_helpers.get_mesos_masters_ips()
    mesos_slaves_ips_list= setup_helpers.get_mesos_slaves_ips()
    setup(step)

