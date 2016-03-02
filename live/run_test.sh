#!/bin/bash
if [ "$1" == "pub" ] ; then
./target/dist/mScale-0.1.0/scripts/launch_zmq_pub $2
fi
if [ "$1" == "sub" ] ; then
./target/dist/mScale-0.1.0/scripts/launch_zmq_sub $2 $3
fi
