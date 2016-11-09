#!/usr/bin/python

import argparse
import core
import sys

# TODO: UDP support
# TODO: add an option to specify an interval of data to fuzz
# TODO: add an option to specify a log file of an application which is being fuzzed
#       (for example, the fuzzer can detect ASan reports, and save test number and fuzzed data)

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
parser.add_argument('--seed', help='seed for pseudo-random generator', type=int,
                    default=1)
parser.add_argument('--protocol', help='TCP or UDP', choices=['tcp', 'udp'], default='tcp')
parser.add_argument('--timeout', help='connection timeout', type=int, default=3)
parser.add_argument('--verbose', help='more logs', action='store_true', default=False)
parser.add_argument('--client_fuzzer', help='fuzz data from client to server', action='store_true', default=False)
parser.add_argument('--server_fuzzer', help='fuzz data from server to client', action='store_true', default=False)

# create configuration
config = core.Config()
config.readargs(parser.parse_args())

# set global configuration
core.config = config

client_fuzzer = None
if config.client_fuzzer:
    client_fuzzer = core.DumbByteArrayFuzzer(config)

server_fuzzer = None
if config.server_fuzzer:
    server_fuzzer = core.DumbByteArrayFuzzer(config)

if server_fuzzer == None and client_fuzzer == None:
    print('Please specify fuzzer mode with --client_fuzzer and --server_fuzzer options')
    sys.exit(1)

if config.protocol == 'tcp':
    server = core.Server(config, client_fuzzer, server_fuzzer)
    server.start()
elif config.protocol == 'udp':
    raise Exception('UDP is not supported yet')
