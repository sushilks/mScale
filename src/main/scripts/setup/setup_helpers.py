import sys
import os
from shell_command import shell_call
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
from six.moves import input
from tempfile import mkstemp

project="festive-courier-755"
zone="us-central1-f"
credentials = GoogleCredentials.get_application_default()
compute = discovery.build('compute', 'v1', credentials=credentials)
email_id="tahir"
_USER="plumgrid"

# *****************************************************************************
# Function: run_cmd_gci
# Purpose : Run command on Google Cloud instance.
# Usage   : run_cmd_gci <cloud_instance_ip>
# *****************************************************************************
def run_cmd_gci(instance_ip, cmd, ssh_flags="-t"):
  shell_cmd="ssh " + ssh_flags + " -o UserKnownHostsFile=/dev/null -o CheckHostIP=no -o StrictHostKeyChecking=no -o ServerAliveInterval=50 -o ConnectionAttempts=3 -o ServerAliveCountMax=5 " + _USER + "@" + instance_ip + " " + cmd
  print (shell_cmd)
  shell_call(shell_cmd)

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

def upload_file(instance_ip, pathname, destination="/home/plumgrid"):
  shell_cmd="scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o CheckHostIP=no -r " + pathname + " " + _USER + "@" + instance_ip + ":" + destination
  print shell_cmd
  shell_call(shell_cmd)

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
  (fd, pathname) = mkstemp(prefix="zk_conf_")
  tfile = os.fdopen(fd, "w")
  conf = """sudo bash -c 'cat > /etc/zookeeper/conf/zoo.cfg' <<DELIM__
""" + conf + """
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

