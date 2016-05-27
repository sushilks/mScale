import os
import argparse
import setup_helpers
from fabric.api import *
import ntpath

parser = argparse.ArgumentParser(description='Hydra setup script')
parser.add_argument('--setup_ips_dir', '-i', type=str, default=os.environ['HOME'], help='Directory where mesos_masters_ips, mesos_slaves_ips and mesos_all_ips files are located. Default is /home/$USER')

parser.add_argument('--start', '-r', type=int, default=1, help='start step')
parser.add_argument('--end', '-e', type=int, default=5, help='end step')
args = parser.parse_args()

setup_ips_dir = args.setup_ips_dir
mesos_all_ips_list = setup_helpers.get_mesos_all_ips(setup_ips_dir)
mesos_masters_ips_list = setup_helpers.get_mesos_masters_ips(setup_ips_dir)
mesos_slaves_ips_list= setup_helpers.get_mesos_slaves_ips(setup_ips_dir)
dst_work_dir = os.environ['HOME']
dst_user_name = os.environ['USER']

# TODO: Check whether IPs files exist?
def setup(step):
  if step == 1:
    print "==> Clone hydra on master node"
    setup_helpers.run_cmd_on_host(dst_user_name, mesos_masters_ips_list[0], "sudo apt-get -y install git unzip")
    setup_helpers.run_cmd_on_host(dst_user_name, mesos_masters_ips_list[0], "wget https://github.com/sushilks/hydra/archive/master.zip && unzip master.zip")
    print "==> Install protobuf on all nodes"
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_all_ips_list, "wget http://launchpadlibrarian.net/160197953/libprotobuf7_2.4.1-3ubuntu4_amd64.deb")
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_all_ips_list, "dpkg -i ./libprotobuf7_2.4.1-3ubuntu4_amd64.deb", use_sudo=True)

  elif step == 2:
    print "==> Add grouping to slaves so that you can steer the workload"
    script_path_name = os.getcwd() + "/vm_files/add_grouping.sh"
    script_name=ntpath.basename(script_path_name)

    print ("==> Uploading %s to %s" % (script_path_name, dst_work_dir))
    setup_helpers.upload_to_multiple_hosts(dst_user_name, mesos_slaves_ips_list, script_path_name, dst_work_dir)

    f = open(setup_ips_dir + '/.mesos_slaves_ips', 'r')
    for ip in f:
      ip = ip.strip()
      instance_tag = setup_helpers.get_instance_tag(ip)
      setup_helpers.run_cmd_on_host(dst_user_name, ip, "/bin/bash " + dst_work_dir + "/" + script_name + " " + instance_tag)

  elif step == 3:
    print "==> Upload conf file"
    script_path_name = setup_helpers.create_hydra_conf(mesos_masters_ips_list[0])
    script_name = ntpath.basename(script_path_name)

    print ("==> Uploading %s to %s" % (script_path_name, dst_work_dir))
    setup_helpers.upload_to_host(dst_user_name, mesos_masters_ips_list[0], script_path_name, dst_work_dir + "/hydra-master")

  elif step == 4:
    print "==> Install packages for hydra on master"
    script_path_name = os.getcwd() + "/vm_files/hydra_pkgs_install.sh"
    script_name=ntpath.basename(script_path_name)

    print ("==> Uploading %s to %s" % (script_path_name, dst_work_dir))
    setup_helpers.upload_to_multiple_hosts(dst_user_name, mesos_masters_ips_list, script_path_name, dst_work_dir)

    print ("==> Running %s/%s script" % (dst_work_dir, script_name))
    #setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_masters_ips_list, "/bin/bash " + dst_work_dir + "/" + script_name + " " + dst_work_dir)

  elif step == 5:
    print "==> Install packages for hydra on slave"
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_slaves_ips_list, "apt-get install -y python-dev python-pip libzmq3-dev libtool pkg-config build-essential autoconf automake", use_sudo=True)
    setup_helpers.run_cmd_on_multiple_hosts(dst_user_name, mesos_slaves_ips_list, "pip install psutil pyzmq protobuf pika", use_sudo=True)

if __name__ == "__main__":
  for step in range(args.start, args.end+1):
    print ("******************* starting step %d ***********************" % step)
    setup(step)

