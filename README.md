# hydra [![Build Status](https://travis-ci.org/sushilks/hydra.svg?branch=master)](https://travis-ci.org/sushilks/hydra)
A Scale Testing infra using Mesos and Marathon

This is a work in progress.

The framework design is to be able to stress any distributed system with client load.
simulate 10's of thousands of clients interacting with the system.

## Requirements to setup

Install a cluster of nodes with Mesos and install Marathon on top of mesos.

Quick way to install this is to follow instructions at
[LINK](https://open.mesosphere.com/getting-started/install/)

I used ubuntu 14.04 as base when installing and had to additional java-8 repo

`sudo add-apt-repository ppa:openjdk-r/ppa`

download libprotobuf7 from http://launchpadlibrarian.net/160197953/libprotobuf7_2.4.1-3ubuntu4_amd64.deb
and install 

`sudo dpkg -i ./libprotobuf7_2.4.1-3ubuntu4_amd64.deb`


Following modification are needed on the slaves
> Add grouping to slaves so that you can steer the workload
> Add additional port resources
> Increase limit on open FD's

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

I would also recommend virtualenv to run/test the project.
I used the following commands
```
pip install virtualenv
virtualenv ../venv
source ../venv/bin/activate
```

### Install pybuilder
`pip install pybuilder`

### Install all the dependencies
`pyb install_dependencies`

### Install the hydra package
`pyb install`

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

There is a CLI mode to get some interaction with the running tests.
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