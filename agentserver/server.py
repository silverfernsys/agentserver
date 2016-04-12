#!/usr/bin/env python
import logging
import signal
import threading
import time
import tornado.ioloop
import tornado.web
import tornado.httpserver
from config import config
from db import dal, tal, Agent, SupervisorSeries
from http import HTTPVersionHandler, HTTPCommandHandler, HTTPStatusHandler, HTTPTokenHandler
from ws import SupervisorAgentHandler, SupervisorCommandHandler, SupervisorStatusHandler

from datetime import datetime, timedelta

class Server():
    # Adapted from code found at https://gist.github.com/mywaiting/4643396
    def sig_handler(self, sig, frame):
        self.logger.warning("Caught signal: %s", sig)
        # Flush AgentWSHandler in order to save
        # timeseries data to database.
        # AgentWSHandler.Flush()
        tornado.ioloop.IOLoop.instance().add_callback(self.shutdown)

    def __init__(self):
    	dal.connect(config.data['database'])
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
            # (r'/rabbitmq/', RabbitMQAgentHandler),
            # (r'/postgresql/', PostgreSQLAgentHandler),
        ])

        # This is where we initialize the TimeseriesAccessLayer connection pool.
        # for agent in dal.Session().query(Agent):
        #     dbname = agent.timeseries_database_name
        #     tal.connect(config.data['timeseries'], dbname)

        # This is where we can test out our query.
        # connection = tal.connection('supervisor_10_0_0_11')
        # print('connection: %s' % connection)
        # query = 'select * from supervisor'
        # resultset = connection.query(query)

        # points = resultset.get_points(measurement='supervisor', tags={'processgroup': 'agenteventlistener'})
        # print('points: %s' % list(points))

        # print(len([resultset]))
        # processes = [('celery', 'celery'), \
        #     ('web', 'web'), \
        #     ('agenteventlistener', 'agenteventlistener'), \
        #     ('supervisoragent', 'supervisoragent')]
        # d = datetime.now() - timedelta(days=10)
        # res = SupervisorSeries.Aggregate(resultset, processes, d, 10, SupervisorSeries.Max)
        # print('res: %s' % res)
        # print('resultset: %s' % resultset)

        # flush_stats_thread = threading.Thread(target=self.flush, args=())
        # flush_stats_thread.daemon = True
        # flush_stats_thread.start()

        self.max_wait_seconds_before_shutdown = config.data['max_wait_seconds_before_shutdown']
        port = config.data['port']
        server = tornado.httpserver.HTTPServer(application)
        server.listen(port)
        self.logger.info('Running on port %s' % port)
        self.server = server
        signal.signal(signal.SIGTERM, self.sig_handler)
        signal.signal(signal.SIGINT, self.sig_handler)
        tornado.ioloop.IOLoop.instance().start()
        self.logger.info("Exit...")

    # def flush(self):
    #     while True:
    #         AgentWSHandler.Flush()
    #         time.sleep(config.data['flush_data_period']) 

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
