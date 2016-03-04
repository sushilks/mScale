__author__ = 'sushil'

from threading import Thread
import os
import sys
import requests

try:
    # Python 2.x
    from SocketServer import ThreadingMixIn
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    from BaseHTTPServer import HTTPServer
except ImportError:
    # Python 3.x
    from socketserver import ThreadingMixIn
    from http.server import SimpleHTTPRequestHandler, HTTPServer


class MyHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        if False and self.server.logging:
            SimpleHTTPRequestHandler.log_message(self, format, *args)


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


class TServer(Thread):
    def __init__(self, port, directory):
        Thread.__init__(self)
        self.port = port
        self.directory = directory
        self.stopServer = False

    def run(self):
        print ("Started a http server to serve content form ./live folder at port %d" % self.port)
        os.chdir(self.directory)
        self.server = ThreadingSimpleServer(('', self.port), MyHandler)
        try:
            while not self.stopServer:
                sys.stdout.flush()
                self.server.handle_request()
            print "Exiting from server"
            return
        except KeyboardInterrupt:
            print "Stopping the HTTP Server"

    def stop(self):
        self.stopServer = True
        print "Calling Server shutdown"
        requests.get('http://localhost:' + str(self.port))
