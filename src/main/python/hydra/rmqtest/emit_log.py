#!/usr/bin/env python
import pika
import sys


# Init RabbitMq PUB
#credentials = pika.PlainCredentials('hydra', 'hydra')
#r_pub_conn = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credentials))
r_pub_conn = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = r_pub_conn.channel()
channel.exchange_declare(exchange='pub',
                         type='fanout')

msg_cnt = 0
for x in range(1000):
    messagedata = "msg%d" % msg_cnt
    msg_cnt += 1
    message = "%d %s" % (msg_cnt, messagedata)
    channel.basic_publish(exchange='pub',
                          routing_key='',
                          body=message)
    print(" [x] Sent %r" % message)
print "done sending all data"
r_pub_conn.close()
