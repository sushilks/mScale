import sys
import os
from shell_command import shell_call
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
from six.moves import input
from tempfile import mkstemp
from fabric.api import *

project="festive-courier-755"
zone="us-central1-f"
credentials = GoogleCredentials.get_application_default()
compute = discovery.build('compute', 'v1', credentials=credentials)
email_id="tahir"
_USER="plumgrid"
DST_WORK_DIR="/home/plumgrid/"

def tryexec(command):
  try:
    exec command
  except SyntaxError as err:
    print command
    print err.lineno
    sys.exit(1)

# *****************************************************************************
# Function: run_cmd_gci
# Purpose : Run command on Google Cloud instance.
# Usage   : run_cmd_gci <cloud_instance_ip>
# *****************************************************************************
def run_cmd_gci(instance_ip, cmd, ssh_flags="-t"):
  shell_cmd="ssh " + ssh_flags + " -o UserKnownHostsFile=/dev/null -o CheckHostIP=no -o StrictHostKeyChecking=no -o ServerAliveInterval=50 -o ConnectionAttempts=3 -o ServerAliveCountMax=5 " + _USER + "@" + instance_ip + " " + cmd
  print (shell_cmd)
  shell_call(shell_cmd)

# Function to get mesos instances ips as a list.
# IPs have already been written in a file.
def get_mesos_x_ips(x="all"):
  if x == "masters":
    file_path_name = os.environ['HOME'] + '/mesos_masters_ips'
  elif x == "slaves":
    file_path_name = os.environ['HOME'] + '/mesos_slaves_ips'
  elif x == "all":
    file_path_name = os.environ['HOME'] + '/mesos_all_ips'

  try:
    f = open(file_path_name)
    ips = [line.rstrip('\n') for line in f]
    f.close
  except:
    print ("WARN: Perhaps file %s does not exist" % file_path_name)
  return ips

def get_mesos_all_ips():
  return get_mesos_x_ips("all")

def get_mesos_masters_ips():
  return get_mesos_x_ips("masters")

def get_mesos_slaves_ips():
  return get_mesos_x_ips("masters")

# Function to get gcloud instances ips.
# It is only for GCE.
def get_master_instances_ips():
  filt = "name eq " + email_id + "-master.*"
  results = compute.instances().list(project=project, zone=zone, filter=filt).execute()
  ips = list()
  for instance in results['items']:
    ips.append(instance["networkInterfaces"][0]["networkIP"])
  return ips

def get_slave_instances_ips():
  filt = "name eq " + email_id + "-slave.*"
  results = compute.instances().list(project=project, zone=zone, filter=filt).execute()
  ips = list()
  for instance in results['items']:
    ips.append(instance["networkInterfaces"][0]["networkIP"])
  return ips

def upload_file(instance_ip, pathname, dst_path):
  shell_cmd="scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o CheckHostIP=no -r " + pathname + " " + _USER + "@" + instance_ip + ":" + dst_path
  print shell_cmd
  shell_call(shell_cmd)

def upload_to_host(dst_user_name, instance_ip, src_pathname, dst_path, use_sudo=False):
  with settings(host_string=instance_ip, user=dst_user_name):
    if use_sudo:
      put(src_pathname, dst_path, use_sudo=True)
    else:
      put(src_pathname, dst_path)

# Assumes that all hosts have same username. If your hostnames are different then
# use upload_to_host() function.
def upload_to_multiple_hosts(dst_user_name, hosts_list, src_pathname, dst_path, use_sudo=False):
  for instance_ip in hosts_list:
    if use_sudo:
      upload_to_host(dst_user_name, instance_ip, src_pathname, dst_path, use_sudo=True)
    else:
      upload_to_host(dst_user_name, instance_ip, src_pathname, dst_path)

def run_cmd_on_host(dst_user_name, instance_ip, cmd, use_sudo=False):
  with settings(host_string=instance_ip, user = dst_user_name):
    if use_sudo:
      sudo(cmd)
    else:
      run(cmd)

# Assumes that all hosts have same username. If your hostnames are different then
# use upload_to_host() function.
def run_cmd_on_multiple_hosts(dst_user_name, hosts_list, cmd, use_sudo=False):
  for instance_ip in hosts_list:
    if use_sudo:
      run_cmd_on_host(dst_user_name, instance_ip, cmd, use_sudo=True)
    else:
      run_cmd_on_host(dst_user_name, instance_ip, cmd)

def create_add_mesosphere_repo_script():
  # mkstemp() returns a tuple containing an OS-level handle to an open file and the absolute pathname of that file
  (fd, pathname) = mkstemp(prefix="add_mesos_repo_")
  tfile = os.fdopen(fd, "w")
  string = """sudo apt-key adv --keyserver keyserver.ubuntu.com --recv E56151BF
DISTRO=$(lsb_release -is | tr '[:upper:]' '[:lower:]')
CODENAME=$(lsb_release -cs)
echo "deb http://repos.mesosphere.io/${DISTRO} ${CODENAME} main" | sudo tee /etc/apt/sources.list.d/mesosphere.list"""
  tfile.write(string)
  tfile.close()
  return pathname

def create_jave_runtime_headless_install_script():
  (fd, pathname) = mkstemp(prefix="jrh_")
  tfile = os.fdopen(fd, "w")
  string = """sudo add-apt-repository ppa:webupd8team/java
echo debconf shared/accepted-oracle-license-v1-1 select true | sudo debconf-set-selections
echo debconf shared/accepted-oracle-license-v1-1 seen true | sudo debconf-set-selections
sudo apt-get -y update
sudo apt-get -y install oracle-java8-installer
sudo apt-get -y install oracle-java8-set-default"""
  tfile.write(string)
  tfile.close()
  return pathname

def create_zk_conf_script(conf):
  pathname = "/tmp/zoo.cfg"
  tfile = open(pathname, 'w')
  conf = conf + """
tickTime=2000
initLimit=10
syncLimit=5
dataDir=/var/lib/zookeeper
clientPort=2181
DELIM__"""
  tfile.write(conf)
  tfile.close()
  return pathname

def create_marathon_conf_script(conf):
  (fd, pathname) = mkstemp(prefix="marathon_conf_")
  tfile = os.fdopen(fd, "w")
  string = """sudo mkdir -p /etc/marathon/conf
sudo cp /etc/mesos-master/hostname /etc/marathon/conf
sudo cp /etc/mesos/zk /etc/marathon/conf/master
echo """ + conf + """ | sudo tee /etc/marathon/conf/zk
sudo service zookeeper restart
sudo service mesos-master restart
sudo service marathon restart
"""
  tfile.write(string)
  tfile.close()
  return pathname

