===============================================================================
Hydra RabbitMQ scale test

===============================================================================
**** RabbitMQ server install *****:

 The following needs to be done on each slave:
   - Add the following line to your /etc/apt/sources.list
     deb http://www.rabbitmq.com/debian/ testing main
   - wget https://www.rabbitmq.com/rabbitmq-signing-key-public.asc
   - sudo apt-key add rabbitmq-signing-key-public.asc
   - sudo apt-get install rabbitmq-server

reference: https://www.rabbitmq.com/install-debian.html

You can check the rabbitmq status by using the ctl:
sudo rabbitmqctl status

*** Add a user with appropriate permissions for the default vhost for rabbitmq ****
sudo rabbitmqctl add_user hydra hydra
sudo rabbitmqctl set_user_tags hydra administrator
sudo rabbitmqctl set_permissions hydra ".*" ".*" ".*"

reference: https://www.rabbitmq.com/man/rabbitmqctl.1.man.html


Finally install rabbitmq python client pika:
sudo pip install pika

=====================================================================================


*To run*:
Create your hydra.ini with your mesos, marathon credentials


*install*:
pip uninstall -y hydra && pyb install

*Example run command*:
hydra rmqfixed


*RESULTS*:
Example results:

INFO 2016-03-29 06:54:30,296 runtest.py:result_parser:210 Total number of clients experiencing packet drop = 100 out of 100 clients
INFO 2016-03-29 06:54:30,296 runtest.py:result_parser:211 Average rate seen at the failing clients 179.802547
INFO 2016-03-29 06:54:30,296 runtest.py:result_parser:215 Total packet's send by PUB:141680 and average packets received by client:17952
INFO 2016-03-29 06:54:30,296 runtest.py:result_parser:217 Average rate seen at the pub 1487.161987 and at clients 179.802547
INFO 2016-03-29 06:54:30,297 boundary.py:boundary_run:111  Run Result = {'average_packet_loss': 87.32901609260306,
 'average_packets': 17952L,
 'average_rate': 179.80254745483398,
 'average_tx_rate': 1487.1619873046875,
 'client_count': 100,
 'failing_clients': 100,
 'failing_clients_rate': 179.80254745483398,
 'packet_tx': 141680L,
 'pub_cpu': 14.247525994640986,
 'pub_net_rxrate': 2325299.542088697,
 'pub_net_txrate': 2325875.568524695}
INFO 2016-03-29 06:54:30,297 boundary.py:boundary_run:111  Run Result = {'average_packet_loss': 87.32901609260306,
 'average_packets': 17952L,
 'average_rate': 179.80254745483398,
 'average_tx_rate': 1487.1619873046875,
 'client_count': 100,
 'failing_clients': 100,
 'failing_clients_rate': 179.80254745483398,
 'packet_tx': 141680L,
 'pub_cpu': 14.247525994640986,
 'pub_net_rxrate': 2325299.542088697,
 'pub_net_txrate': 2325875.568524695}
INFO 2016-03-29 06:54:30,297 runtest.py:boundary_resultfn:152 Completed run with message rate = 10000 and client count=100 Reported Rate PUB:1487.161987 SUB:179.802547 and Reported Drop Percentage : 87.329016
