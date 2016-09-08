#!/usr/bin/env python
import logging
import signal
import sys
import time
import tornado.ioloop
import tornado.web
import tornado.httpserver
from configutil import ConfigError
from pyfiglet import figlet_format
from setproctitle import setproctitle
from termcolor import cprint

from agentserver.config.server import config
from agentserver.db.models import models
from agentserver.db.timeseries import kafka, druid
from agentserver.http.client import (HTTPVersionHandler, HTTPTokenHandler,
                         HTTPDetailHandler, HTTPCommandHandler,
                         HTTPListHandler)
from agentserver.http.agent import HTTPAgentUpdateHandler, HTTPAgentDetailHandler
from agentserver.ws.agent import SupervisorAgentHandler
from agentserver.ws.client import SupervisorClientHandler
from agentserver.clients.supervisorclientcoordinator import scc
from agentserver.utils.log import config_logging, LoggingError
from agentserver import __version__


class Server(object):
    # Adapted from code found at https://gist.github.com/mywaiting/4643396

    def sig_handler(self, sig, frame):
        self.logger.warning("Caught signal: %s", sig)
        tornado.ioloop.IOLoop.instance().add_callback(self.shutdown)

    def __init__(self, config):
        setproctitle('agentserver')
        try:
            config.parse()
        except ConfigError as e:
            print('{0} Exiting.'.format(e.message))
            sys.exit(1)
        try:
            config_logging(config)
        except LoggingError as e:
            print('{0} Please run server as root. Exiting.'.format(e.message))
            sys.exit(1)
        self.print_splash_page()
        self.connect(config.arguments.agentserver.database,
            config.arguments.agentserver.kafka,
            config.arguments.agentserver.druid)
        self.logger = logging.getLogger('Web Server')
        scc.initialize()

        application = tornado.web.Application([
            (r'/', HTTPVersionHandler),
            (r'/token/', HTTPTokenHandler),
            (r'/list/', HTTPListHandler),
            (r'/command/', HTTPCommandHandler),
            (r'/detail/', HTTPDetailHandler),
            (r'/agent/update/', HTTPAgentUpdateHandler),
            (r'/agent/detail/', HTTPAgentDetailHandler),
            (r'/supervisor/', SupervisorAgentHandler),
            (r'/client/supervisor', SupervisorClientHandler),
        ])

        self.max_wait_seconds_before_shutdown = int(
            config.arguments.agentserver.max_wait_seconds_before_shutdown)
        port = config.arguments.agentserver.port
        server = tornado.httpserver.HTTPServer(application)
        server.listen(port)
        self.logger.info('Running on port {0}'.format(port))
        self.server = server
        signal.signal(signal.SIGTERM, self.sig_handler)
        signal.signal(signal.SIGINT, self.sig_handler)
        tornado.ioloop.IOLoop.instance().start()
        self.logger.info("Exit...")

    def connect(self, db_uri, kafka_uri, druid_uri):
        try:
            models.connect(db_uri)
            kafka.connect(kafka_uri)
            druid.connect(druid_uri)
        except Exception as e:
            print(e.message)
            sys.exit(1)

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
            text = figlet_format('AgentServer', width=120,
                                 font='slant').rstrip()
            cprint(text, 'red', attrs=['blink'])
            width = reduce(max, map(len, text.split('\n')))
            title = 'AgentServer v{0}'.format(__version__)
            centered_title = title.center(width, ' ')
            cprint(centered_title, 'red')


def main():
    Server(config)


if __name__ == "__main__":
    main()
