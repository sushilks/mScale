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

def get_email_id():
  f = open(os.environ['HOME'] + "/.aurora.conf")
  for line in f:
    if 'emailid' in line:
      return line.rstrip('\n').split("emailid=",1)[1]

# Function to get mesos instances ips as a list.
# IPs have already been written in a file.
def get_mesos_x_ips(setup_ips_dir, x="all"):
  if x == "masters":
    file_path_name = setup_ips_dir + '/mesos_masters_ips'
  elif x == "slaves":
    file_path_name = setup_ips_dir + '/mesos_slaves_ips'
  elif x == "all":
    file_path_name = setup_ips_dir + '/mesos_all_ips'

  try:
    f = open(file_path_name)
    ips = [line.rstrip('\n') for line in f]
    f.close
  except:
    print ("WARN: Perhaps file %s does not exist" % file_path_name)
    return
  return ips

# Get all IP addresses (both masters and slaves)
def get_mesos_all_ips(setup_ips_dir):
  return get_mesos_x_ips(setup_ips_dir, x="all")

# Get master IP addresses
def get_mesos_masters_ips(setup_ips_dir):
  return get_mesos_x_ips(setup_ips_dir, x="masters")

# Get Slaves IPs
def get_mesos_slaves_ips(setup_ips_dir):
  return get_mesos_x_ips(setup_ips_dir, x="slaves")

# Function to get gcloud instances ips.
# It is only for GCE.
def get_master_instances_ips():
  email_id = get_email_id()
  filt = "name eq " + email_id + "-master.*"
  results = compute.instances().list(project=project, zone=zone, filter=filt).execute()
  ips = list()
  for instance in results['items']:
    ips.append(instance["networkInterfaces"][0]["networkIP"])
  return ips

def get_slave_instances_ips():
  email_id = get_email_id()
  filt = "name eq " + email_id + "-slave.*"
  results = compute.instances().list(project=project, zone=zone, filter=filt).execute()
  ips = list()
  for instance in results['items']:
    ips.append(instance["networkInterfaces"][0]["networkIP"])
  return ips

def spawn_instance(instance_name, os_name, machine_type="n1-standard-4", dst_user="plumgrid"):
  instance_name = email_id + "-" + instance_name # Prefix emailid before instance name.
  #(fd, pathname) = mkstemp(prefix="gce_key_")
  pathname="/tmp/gce_key.txt"
  tfile = open(pathname, 'w')
  #tfile = os.fdopen(fd, "w")

  with open("/home/muneeb/.ssh/id_rsa.pub") as f:
    lines = f.readlines()
    tfile.writelines(dst_user + ":" + lines[0])
    tfile.write(dst_user + ":" + COMMON_KEY + "\n")
  print("pathname=%s" % pathname)
  #key_cmd="echo plumgrid:$(cat " + os.environ['HOME'] + "/.ssh/id_rsa.pub) > " + pathname + " && echo plumgrid:$(echo " + COMMON_KEY + ") >> " + pathname
  #shell_call(key_cmd)

  print ("Creating the disk[%s-d1] for the instance" % instance_name)
  disk1_cmd="gcloud compute disks create " + instance_name + "-d1 --image " + os_name + " --type pd-standard --size=30GB -q"
  print("disk1_cmd=%s" %disk1_cmd)
  shell_call(disk1_cmd)
  print ("Creating the disk[%s-d2] for the instance" % instance_name)
  disk2_cmd="gcloud compute disks create " + instance_name + "-d2 --type pd-standard --size=75GB -q"
  print("disk2_cmd=%s" %disk2_cmd)
  shell_call(disk2_cmd)
  print ("Creating the instance[instance_name] ")
  cmd = "gcloud compute instances create " + instance_name + " --machine-type " + machine_type + \
        " --network net-10-10 --maintenance-policy MIGRATE --scopes https://www.googleapis.com/auth/cloud-platform --disk name=" + \
        instance_name + "-d1,mode=rw,boot=yes,auto-delete=yes --disk name=" + instance_name + \
        "-d2,mode=rw,boot=no,auto-delete=yes --no-address --tags no-ip --metadata-from-file sshKeys=" + pathname
  print ("create_instance_cmd=%s" %cmd)
  shell_call(cmd)

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

def create_zk_conf_script(conf):
  pathname = "/tmp/zoo.cfg"
  tfile = open(pathname, 'w')
  conf = conf + """
tickTime=2000
initLimit=10
syncLimit=5
dataDir=/var/lib/zookeeper
clientPort=2181
"""
  tfile.write(conf)
  tfile.close()
  return pathname

def create_slave_conf_script(ip):
  (fd, pathname) = mkstemp(prefix="slave_conf_")
  tfile = os.fdopen(fd, "w")
  script = """
# ZooKeeper will be pulled in and installed as a dependency automatically.
# The slaves do not require to run their own zookeeper instances
  sudo service zookeeper stop
  sudo bash -c "echo manual | sudo tee /etc/init/zookeeper.override"
# make sure the Mesos master process doesn't start on our slave servers.
  sudo bash -c "echo manual | sudo tee /etc/init/mesos-master.override"
  sudo service mesos-master stop || true
  echo """ + ip + """ | sudo tee /etc/mesos-slave/ip
  sudo cp /etc/mesos-slave/ip /etc/mesos-slave/hostname
  sudo service mesos-slave stop || true
  sudo service mesos-slave start
#  sudo apt-get -y install python-dev python-pip
#  sudo apt-get -y install libzmq3-dev libtool pkg-config build-essential autoconf automake
#  sudo pip install psutil pyzmq protobuf
"""
  tfile.write(script)
  tfile.close()
  return pathname

def config_section_map(config, section):
  options_dict = {}
  options = config.options(section)
  for option in options:
    try:
      options_dict[option] = config.get(section, option)
      print ("*** %s=%s" %(option, options_dict[option]))
      if options_dict[option] == -1:
        DebugPrint("skip: %s" % option)
    except:
      print("exception on %s!" % option)
      options_dict[option] = None
  return options_dict

def create_hydra_conf(master_node_ip):
  pathname = "/tmp/hydra.ini"
  tfile = open(pathname, 'w')
  string = """[marathon]
ip: """ + master_node_ip + """
port: 8080
app_prefix: g1

[mesos]
ip: """ + master_node_ip + """
port: 5050

[hydra]
port: 9800
dev: eth0
"""
  tfile.write(string)
  tfile.close()
  return pathname

