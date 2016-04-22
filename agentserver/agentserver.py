#! /usr/bin/env python
import argparse
import logging
import signal
import sys
import time
from setproctitle import setproctitle
from server.config import config
from server.server import Server

def main():
    setproctitle('agentserver')
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="configuration file to read -- /etc/agentserver/agentserver.conf otherwise")
    parser.add_argument("--log_level", help="log level")
    parser.add_argument("--log_file", help="log file path")
    parser.add_argument("--database", help="the database connection protocol://username:password@host:port/dbname")
    parser.add_argument("--timeseries", help="the timeseries database protocol://username:password@host:port")
    parser.add_argument("--max_wait_seconds_before_shutdown", help="the number of seconds to wait before shutting down server")
    parser.add_argument("--url", help="server url")
    parser.add_argument("--port", help="server port")
    args = parser.parse_args()

    try:
        config.resolveArgs(args)
        if config.isResolved():
            logging.basicConfig(filename=config.log_file, format='%(asctime)s::%(levelname)s::%(name)s::%(message)s', level=logging.DEBUG)
            if sys.stdout.isatty():
                logger = logging.getLogger()
                channel = logging.StreamHandler(sys.stdout)
                logger.addHandler(channel)
            server = Server()
        else:
            sys.stderr.write('ERROR: resolving configuration.\n')
            sys.exit(1)     
    except Exception as e:
        print('AgentServer Exception. DETAILS: %s' % e)


if __name__ == "__main__":
    main()