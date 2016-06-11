#!/usr/bin/python
import zmq
import sys

server_ip = sys.argv[1]

context = zmq.Context()
print("Connecting to hello world server")
socket = context.socket(zmq.REQ)
socket.connect("tcp://" + server_ip + ":5555")
for request in range(10):
    if request % 2:
        print("Sending request Hello")
        socket.send(b"Hello")
    else:
        print("Sending request 'As salam u alaicum'")
        socket.send(b"As salam u alaicum")
    message = socket.recv()
    print("Received reply %s [ %s ]" % (request, message))
