#!/usr/bin/python

import argparse
import core
import sys

# TODO: UDP support
# TODO: add an option to specify an interval of data to fuzz
# TODO: add an option to specify a log file of an application which is being fuzzed
#       (for example, the fuzzer can detect ASan reports, and save test number and fuzzed data)
# TODO: dump client/server data to separate files for last connection
# TODO: load dumped data from file to be able to reproduce test without running original client/server

parser = argparse.ArgumentParser()
parser.add_argument('--local_host',  help='local host name', default='localhost')
parser.add_argument('--local_port',  help='local port to listen', type=int, default=10101, required=True)
parser.add_argument('--remote_host', help='remote host name', default='localhost')
parser.add_argument('--remote_port', help='remote port', type=int, default=80, required=True)
parser.add_argument('--test',
                    help='test range, it can be a number, or an interval "start:end"')
parser.add_argument('--ratio',
                    help='fuzzing ratio range, it can be a number, or an interval "start:end"',
                    default='0.01:0.05')
parser.add_argument('--protocol', help='TCP or UDP', choices=['tcp', 'udp'], default='tcp')
parser.add_argument('--timeout', help='connection timeout', type=int, default=3)
parser.add_argument('--verbose', help='more logs', action='store_true', default=False)
parser.add_argument('--fuzzer', help='fuzzer mode (client or server), data can be stored to a file specified by --datafile option',
                    choices=['client', 'server'])
parser.add_argument('--dumper', help='dumper mode (client or server), read data from file specified by --datafile option',
                    choices=['client', 'server'])
parser.add_argument('--datafile', help='file for storing and loading data')

# create configuration
config = core.Config()
config.readargs(parser.parse_args())

# set global configuration
core.config = config

if config.protocol == 'tcp':
    server = core.Server(config)
    server.start()
elif config.protocol == 'udp':
    raise Exception('UDP is not supported yet')
