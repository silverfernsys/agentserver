#! /usr/bin/env python
import sys
import os
from argparse import ArgumentParser, Action, ArgumentError


class Echo(object):

    def __init__(self):
        data_dir = os.path.join(os.path.abspath(
            os.path.dirname(__file__)), 'data')

        arg_parser = ArgumentParser()
        command_parser = arg_parser.add_subparsers(
            title='available commands', help='command help',
            dest='command', metavar='')
        command_parser.add_parser(name='memory', 
            help='generate a configuration for an in-memory database')
        command_parser.add_parser(name='mysql',
            help='generate a configuration for a mysql database')
        command_parser.add_parser(name='postgres',
            help='generate a configuration for a postgres database')
        command_parser.add_parser(name='sqlite',
            help='generate a configuration for a sqlite database')
        command_parser.add_parser(name='supervisor', 
            help='generate a configuration for supervisor')
        command_parser.add_parser(name='druid',
            help='generate a configuration for druid')
        
        args = arg_parser.parse_args()

        if args.command == 'memory':
            path = os.path.join(data_dir, 'conf', 'agentserver.conf')
        elif args.command == 'mysql':
            path = os.path.join(data_dir, 'conf', 'mysql-example.conf')
        elif args.command == 'postgres':
            path = os.path.join(data_dir, 'conf', 'postgres-example.conf')
        elif args.command == 'sqlite':
            path = os.path.join(data_dir, 'conf', 'sqlite-example.conf')
        elif args.command == 'supervisor':
            path = os.path.join(data_dir, 'supervisor', 'agentserver.conf')
        elif args.command == 'druid':
            path = os.path.join(data_dir, 'druid', 'tranquility', 'supervisor.json')

        print(open(path).read().strip())


def main():
    Echo()


if __name__ == "__main__":
    main()
