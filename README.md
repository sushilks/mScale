# mScale
A Scale Testing infra using Mesos and Marathon



# Requirements

Install a cluster of nodes with Mesos and install Marathon on top of mesos.
Quick way to install this is to follow instructions at
https://open.mesosphere.com/getting-started/install/

I used ubuntu 14.04 as base when installing and had to additional java-8 repo
sudo add-apt-repository ppa:openjdk-r/ppa


Configuration for starting the tool needs to be provided in form of a .ini file.
An example config is available in src/main/python/config/example_config.ini

I would also recommend virtualenv to run/test the project.
I used the following commands
pip install virtualenv
virtualenv ../venv
source ../venv/bin/activate

Install pybuilder
pip install pybuilder

Install all the dependencies
pyb install_dependencies

Install the mScale packet
pyb install

## Running the program
>launch_zmq_scale_test ./src/main/python/config/example_config.ini

If I am testing I use the following command line
pip uninstall -y mScale && pyb install && launch_zmq_scale_test ./src/main/python/config/example_config.ini