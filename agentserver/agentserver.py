#! /usr/bin/env python
import argparse
import logging
import signal
import time
import ConfigParser
from setproctitle import setproctitle
from server import Server
# from utils import resolveConfig
from config import config

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
        config_parser = ConfigParser.ConfigParser()
        config_file_path = args.config or '/etc/agentserver/agentserver.conf'
        config_parser.read(config_file_path)

        config.resolveConfig(config_parser, args)
        logging.basicConfig(filename=config.data['log_file'], format='%(asctime)s::%(levelname)s::%(name)s::%(message)s', level=logging.DEBUG)
        
        server = Server(config.data)
    except Exception as e:
        print('Error loading configuration file at %s.' % config_file_path)
        print('DETAILS: %s' % e)


if __name__ == "__main__":
    main()