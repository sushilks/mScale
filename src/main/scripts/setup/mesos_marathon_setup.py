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
parser.add_argument('--config_file', '-f', type=str, default=os.getcwd() + "/setup_config.ini", help='Setup configuration file')

parser.add_argument('--local_work_dir', '-l', type=str, default=os.environ['HOME'], help='Script will copy all downloaded/output files in this directory')
parser.add_argument('--dst_work_dir', '-w', type=str, default="/home/plumgrid", help='Destination work directory. All contents will be uploaded here.')
parser.add_argument('--dst_user_name', '-u', type=str, default="plumgrid", help='Destination user name')
parser.add_argument('--start', '-r', type=int, default=1, help='start step')
parser.add_argument('--end', '-e', type=int, default=12, help='end step')
parser.add_argument('--clean', '-c', action='store_true', help='cleanup instances')
args = parser.parse_args()

config_file = args.config_file
local_work_dir = args.local_work_dir
dst_work_dir = args.dst_work_dir
dst_user_name=args.dst_user_name

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
    f = open(local_work_dir + '/mesos_all_ips', 'w')
    fm = open(local_work_dir + '/mesos_masters_ips', 'w')
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
  # TODO: Wait for machine to come up and running.
  # ******************************* Install Mesos Sphere on the servers. ********************************
  elif step == 3:
    print "==> Add Mesosphere repository to resources list of ALL hosts"
    script_path_name = os.getcwd() + "/vm_files/add_mesos_sphere_repo_and_install_java.sh"
    script_name=ntpath.basename(script_path_name)

    print ("==> Uploading %s to %s" % (script_path_name, dst_work_dir))
    setup_helpers.upload_to_multiple_hosts(dst_user_name, mesos_all_ips_list, script_path_name, dst_work_dir)

    print ("==> Running %s/%s script" % (dst_work_dir, script_name))
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_all_ips_list, "/bin/bash " + dst_work_dir + "/" + script_name)

  elif step == 4:
    print "==> On master hosts, install mesos and marathon package"
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_masters_ips_list, "sudo apt-get install -y mesos marathon")

    # For your slave hosts, you only need the mesos package, which also pulls in zookeeper as a dependency:
    print "==> On slave hosts, install mesos package"
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_slaves_ips_list, "sudo apt-get -y install mesos")

  elif step == 5:
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
    print "***************************************************************************************************"
    print ("IPs files are located at " + local_work_dir + " . You may need to give this location to your hydra_setup script." )
    print "***************************************************************************************************"


if __name__ == "__main__":
  if args.clean:
    shell_call("aurora rm instances master*")
    shell_call("aurora rm instances slave*")
    shell_call("rm ~/mesos_all_ips")
    shell_call("rm ~/mesos_masters_ips")
    shell_call("rm ~/mesos_slaves_ips")
    #shell_call("sudo apt-get install python-pip")
    #shell_call("sudo pip install shell_command google-api-python-client fabric")
  else:
    for step in range(args.start, args.end+1):
      print ("******************* starting step %d ***********************" % step)
      mesos_all_ips_list = setup_helpers.get_mesos_all_ips(local_work_dir)
      mesos_masters_ips_list = setup_helpers.get_mesos_masters_ips(local_work_dir)
      mesos_slaves_ips_list= setup_helpers.get_mesos_slaves_ips(local_work_dir)
      setup(step)

