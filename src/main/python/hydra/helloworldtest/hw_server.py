#!/usr/bin/python

import time
import zmq

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

while True:
    #  Wait for next request from client
    message = socket.recv()
    print("Received request: %s" % message)

    #  Do some 'work'
    time.sleep(1)

    #  Send reply back to client
    if message == "Hello":
        socket.send_string("Hi")
    elif message == "As salam u alaicum":
        socket.send_string("Wa alaicum us salam")
