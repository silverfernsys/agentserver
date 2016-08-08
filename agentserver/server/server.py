#!/usr/bin/env python
import logging
import signal
import sys
import threading
import time
import tornado.ioloop
import tornado.web
import tornado.httpserver
from termcolor import colored, cprint
from config import config
from db import dal, kal, dral, pal
from http import HTTPVersionHandler, HTTPCommandHandler, HTTPStatusHandler, HTTPTokenHandler
from ws import SupervisorAgentHandler, SupervisorCommandHandler, SupervisorStatusHandler

from pyfiglet import figlet_format

from datetime import datetime, timedelta

class Server():
    # Adapted from code found at https://gist.github.com/mywaiting/4643396
    def sig_handler(self, sig, frame):
        self.logger.warning("Caught signal: %s", sig)
        tornado.ioloop.IOLoop.instance().add_callback(self.shutdown)

    def __init__(self):
        self.print_splash_page()
    	dal.connect(config.database)
        kal.connect(config.kafka)
        dral.connect(config.druid)
        pal.connect(config.druid)
    	self.session = dal.Session()
        self.logger = logging.getLogger('Web Server')

        application = tornado.web.Application([
            (r'/', HTTPVersionHandler),
            (r'/cmd/', HTTPCommandHandler),
            (r'/status/', HTTPStatusHandler),
            (r'/token/', HTTPTokenHandler),
            # Commands and Status handlers
            (r'/cmd/supervisor/', SupervisorCommandHandler),
            (r'/status/supervisor/', SupervisorStatusHandler),
            # Agents
            (r'/supervisor/', SupervisorAgentHandler),
        ])

        self.max_wait_seconds_before_shutdown = int(config.max_wait_seconds_before_shutdown)
        port = config.port
        server = tornado.httpserver.HTTPServer(application)
        server.listen(port)
        self.logger.info('Running on port %s' % port)
        self.server = server
        signal.signal(signal.SIGTERM, self.sig_handler)
        signal.signal(signal.SIGINT, self.sig_handler)
        tornado.ioloop.IOLoop.instance().start()
        self.logger.info("Exit...")

    def shutdown(self):
        self.logger.info('Stopping HTTP Server.')
        self.server.stop()
        seconds = self.max_wait_seconds_before_shutdown
        self.logger.info('Will shutdown in %s seconds...', seconds)
        io_loop = tornado.ioloop.IOLoop.instance()
        deadline = time.time() + seconds

        def stop_loop():
            now = time.time()
            if now < deadline and (io_loop._callbacks or io_loop._timeouts):
                io_loop.add_timeout(now + 1, stop_loop)
            else:
                io_loop.stop()
                self.logger.info('Shutdown')
        stop_loop()

    def print_splash_page(self):
        if sys.stdout.isatty():
            text = figlet_format('AgentServer', width=120, font='slant').rstrip()
            cprint(text, 'red', attrs=['blink'])
            width = reduce(max, map(len, text.split('\n')))
            title = 'AgentServer v0.1a'
            centered_title = title.center(width, ' ')
            cprint(centered_title, 'red')
