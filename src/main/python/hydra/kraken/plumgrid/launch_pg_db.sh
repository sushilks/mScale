#!/bin/bash
sudo pkill -9 -f launch_trace_collector
sudo pkill -9 -f launch_broker
/opt/pg/bin/launch_trace_collector -a 12349 -s -l /opt/pg/log/trace_collector_broker.log &
/opt/pg/bin/launch_broker_watchcat -j ${1} -p 8000 -t localhost:12349 -u
