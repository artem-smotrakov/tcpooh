#!/usr/bin/python

import argparse
import helper

# TODO: UDP support

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
parser.add_argument('--client_fuzzer', help='fuzz data from client to server', action='store_true', default=True)
parser.add_argument('--server_fuzzer', help='fuzz data from server to client', action='store_true', default=False)

# create configuration
config = helper.Config()
config.readargs(parser.parse_args())

# set global configuration
helper.config = config

client_fuzzer = None
if config.client_fuzzer:
    client_fuzzer = helper.DumbByteArrayFuzzer(config)

server_fuzzer = None
if config.server_fuzzer:
    server_fuzzer = helper.DumbByteArrayFuzzer(config)

if config.protocol == 'tcp':
    server = helper.Server(config, client_fuzzer, server_fuzzer)
    server.start()
elif config.protocol == 'udp':
    raise Exception('UDP is not supported yet')
