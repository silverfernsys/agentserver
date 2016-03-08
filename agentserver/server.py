#!/usr/bin/env python
import logging
import signal
import time
import tornado.ioloop
import tornado.web
import tornado.httpserver
from db import dal
from http import HTTPVersionHandler, HTTPStatusHandler, HTTPTokenHandler
from ws import AgentWSHandler, UserWSHandler


class Server():
    # Adapted from code found at https://gist.github.com/mywaiting/4643396
    def sig_handler(self, sig, frame):
        self.logger.warning("Caught signal: %s", sig)
        tornado.ioloop.IOLoop.instance().add_callback(self.shutdown)

    def __init__(self, config):
    	dal.connect(config['database'])
    	self.session = dal.Session()
        self.logger = logging.getLogger('Web Server')

        application = tornado.web.Application([
            (r'/', HTTPVersionHandler),
            (r'/status/', HTTPStatusHandler),
            (r'/token/', HTTPTokenHandler),
            (r'/user/', UserWSHandler),
            (r'/agent/', AgentWSHandler),
        ])

        # process_updater = ProcessUpdater(**kwargs)
        # event_server = EventServer(threaded=True)

        self.max_wait_seconds_before_shutdown = config['max_wait_seconds_before_shutdown']
        port = config['port']
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


# SERVER_VERSION = '0.0.1'

# class Server(object):
#     def shutdown(self, sig, frame):
#         self.run_loop = False

#     def __init__(self, config_data):
#         self.run_loop = True
#         self.start_time = time.time()
#         setproctitle('supervisoragent')
#         signal.signal(signal.SIGTERM, self.shutdown)
#         signal.signal(signal.SIGINT, self.shutdown)
#         self.config_data = config_data

#     def run(self):
#         self.run_loop = True
#         processmonitor = ProcessMonitor(sample_interval=self.config_data['sample_interval'],
#             push_interval=self.config_data['push_interval'],
#             token=self.config_data['token'], url=self.config_data['url'])
#         statusserver = StatusServer(self.config_data['port'], self)
#         while self.run_loop:
#             time.sleep(0.1)

#     def data(self):
#         ret_data = self.config_data.copy()
#         ret_data['start_time'] = self.start_time
#         ret_data['server_version'] = SERVER_VERSION
#         return ret_data
        
#         # We're going to shutdown here
#         statusserver.shutdown()
