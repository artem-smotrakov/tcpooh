#!/usr/bin/python

import argparse
import core
import sys

# TODO: UDP support
# TODO: add an option to specify an interval of data to fuzz
# TODO: add an option to specify a log file of an application which is being fuzzed
#       (for example, the fuzzer can detect ASan reports, and save test number and fuzzed data)
# TODO: add a boring client

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
parser.add_argument('--mode', help='fuzzer mode TBD',
                    choices=['fuzz_client', 'fuzz_server', 'client_data', 'server_data'])
parser.add_argument('--data', help='file for storing and loading data')

# create task
task = core.Task()
try:
    task.readargs(parser.parse_args())
    task.run()
finally:
    task.finalize()
