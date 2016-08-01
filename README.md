# hydra [![Build Status](https://travis-ci.org/lake-lerna/hydra.svg?branch=master)](https://travis-ci.org/lake-lerna/hydra)
A Scale Testing infra using Mesos and Marathon

This is a work in progress.

The framework design is to be able to stress any distributed system with client load.
simulate 10's of thousands of clients interacting with the system.

## Requirements to setup

### Install Mesos/Marathon cluster
Hydra uses Mesos/Marathon API to schedule jobs on Mesos cluster. </ br>
A Quick way to install this is to follow instructions at
[LINK](https://open.mesosphere.com/getting-started/install/). </br >
An automated script to setup Mesos/Marathon cluster on Google Cloud 
compute engine instances has also been provided at 
[HydroSphere](https://github.com/lake-lerna/HydroSphere)

### Install Hydra:
Ubuntu 14.04 has been used as base when installing. 
Following steps need to be taken to install Hydra. </br >
a. Clone Hydra
```
git clone git@github.com:lake-lerna/hydra.git
```
b. Hydra uses protobuf for communication. Install that
```
sudo apt-get -y install protobuf-c-compiler protobuf-compiler libprotobuf-dev
```
c. It also requires python packages like websocket-client, pyzmq, 
marathon etc. </br >
Its better to create a virtual environment to install these packages. 
Follow instructions given below to create the environment
```
curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash
echo 'export PATH="/home/plumgrid/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
source ~/.bashrc 
pyenv update
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev
pyenv install 2.7.10
pyenv virtualenv 2.7.10 venv2710 
pyenv shell venv2710
```

NOTE: Above commands are preparing a virtual environment with Python2.7.10,
You can use Python verson 2/2.7/3/3.2/3.3 or 3.4 as well.

d. Please run below commands to install zmq related stuff
```
wget https://raw.githubusercontent.com/zeromq/cppzmq/master/zmq.hpp
mv zmq.hpp /usr/include/zmq.hpp
wget https://github.com/zeromq/zeromq4-1/releases/download/v4.1.4/zeromq-4.1.4.tar.gz
tar xvf zeromq-4.1.4.tar.gz
pushd zeromq-4.1.4
./configure --without-libsodium --prefix=/usr
make -j 4
sudo make install
popd
```

All pre-reqs have been installed. Now, we are all set to install Hydra. <\br > 
Go inside Hydra cloned repo and run

```
pip install pybuilder
pyb install_dependencies --verbose
pyb analyze
pyb publish -x run_unit_tests
pyb install -x run_unit_tests
```

Congratulations! You have installed Hydra. <\br >
There is a CLI mode to get some interaction with the running tests.

To make use of it. Make sure to add these two paths to your .bashrc.

```
echo 'export PATH="$HOME/hydra/src/main/scripts:$PATH"' >> ~/.bashrc
echo 'export PYTHONPATH="$HOME/hydra/src/main/python:$PATH" >> ~/.bashrc
source ~/.bashrc
```
```
>hydra cli
Usage:
   hydra cli ls slaves
   hydra cli ls apps
   hydra cli ls task <app>
   hydra cli [force] stop <app>
   hydra cli scale <app> <scale>
   hydra cli (-h | --help)
   hydra cli --version
```

## Run unit test cases:
------------------------
Unit test cases will practice most of the Hydra library functions. 
You dont need to have actual Mesos/Marathon cluster. It uses a 
mock backend. Everything will be run on local machine. 

Some of the test cases requires RMQ to be installed. So, install that
```
sudo apt-get -y install python-dev python-pip rabbitmq-server
sudo rabbitmqctl add_user hydra hydra
sudo rabbitmqctl set_user_tags hydra administrator
sudo rabbitmqctl set_permissions hydra ".*" ".*" ".*"
```

To run the unit test cases

```
pyb test --verbose
```

## Use Hydra to schedule jobs on Mesos cluster
Following modification are needed on the slaves
1. Add grouping to slaves so that you can steer the workload
2. Add additional port resources
3. Increase limit on open FD's

```
sudo service mesos-slave stop
# Add grouping informaiton
sudo mkdir -p /etc/mesos-slave/attributes/
echo "cpu16:mem60" | sudo tee /etc/mesos-slave/attributes/group
# add additional port resources
echo "ports:[2000-32000]" | sudo tee /etc/mesos-slave/resources
# Linux by default uses port 23768-61000
# if you decide to use any ports in that range you can modify the following
# Tell linux to not use these ports (Add the following to /etc/sysctl.conf file)
# net.ipv4.ip_local_port_range ="40001 60000"

# Tell mesos-slave to cleanup the work area frequently (Otherwise it will fill up)
echo "60mins" | sudo tee /etc/mesos-slave/gc_delay

# Optionally you can change the mesos work directory from /tmp
echo "/opt/mesos" | sudo tee /etc/mesos-slave/work_dir

# Increase FD limits
# Add to the end of /etc/security/limits.conf
* soft     nproc          65535
* hard     nproc          65535
* soft     nofile         65535
* hard     nofile         65535
root soft     nofile         65535
root hard     nofile         65535
# All the old workloads will need to be cleaned up as the slave properties have changed
# only do this if you are sure about deleting old workloads
sudo rm -f /tmp/mesos/meta/slaves/latest
# start the slave
sudo service mesos-slave start
```


Configuration for starting the tool needs to be provided in form of a .ini file.

An example config is available in src/main/python/config/example_config.ini
```
[marathon]
ip: 10.10.0.8
port: 8080
app_prefix: g1

[mesos]
ip: 10.10.0.8
port: 5050
cluster0: slave_id.slave-set1_0
cluster1: slave_id.slave-set1_1
cluster2: slave_id.slave-set1_2

[hydra]
port: 9800
dev: eth0
```

### Running the program
Make sure the use the right .ini file for your setup.

`cp src/main/python/config/example_config.ini ./hydra.ini`

if your current directory has "hydra.ini" then you can omit the ini file form command line

`hydra zmq`

Edit the ini file is located in some other directory

`hydra zmq ./src/main/python/config/example_config.ini`

If I am testing I use the following command line

`pip uninstall -y hydra && pyb install && hydra zmq`

Currently it's not doing much, more work is needed for doing any real testing
Running the above command will connect to mesos/maraton, spin up one zmq publisher
and one zmq subscriber to it.
there after the test will scale the subscribers to 100.
more to come ....



### NOTES
Mesos-Marathon Installation [LINK](https://open.mesosphere.com/getting-started/install/)

Marathon-Python Package [LINK](http://thefactory.github.io/marathon-python/marathon.html#marathon.models.deployment.MarathonDeployment)

Mesos Endpoint API [LINK](http://mesos.apache.org/documentation/latest/endpoints/)

Marathon Docs [LINK](https://mesosphere.github.io/marathon/docs/)

When working with mesos,

To reset the slave and make it forget about old tasks

`sudo rm -rf /tmp/mesos/meta/slaves/latest`

To get logs from a compleated task (Remove --completed if the task is still running)

`./bin/dcos task log --completed zst-sub.e700f205-ea75-11e5-b869-42010a0a01c1 --lines=50 src/main/scripts/p0.stderr.log`

TO get the content of the running task sandbox

`./bin/dcos task ls  zst-sub.5907bc1f-ea15-11e5-b869-42010a0a01c1`


To configure DCOS use the following commands

`./bin/dcos config set core.mesos_master_url http://10.10.0.223:5050`
`./bin/dcos config set marathon.url http://10.10.0.223:8080`
