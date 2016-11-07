#!/usr/bin/python

import socket
import argparse
import textwrap

# TODO: UDP support

# global variables
bufsize = 4096
verbose = False

def verbose(*args):
    if verbose:
        if len(args) == 0:
            return
        elif len(args) == 1:
            print(args[0])
        elif len(args) == 2:
            verbose_with_prefix(args[0], args[1])
        else:
            verbose_with_indent(args[0], args[1], args[2:])

def verbose_with_prefix(prefix, message):
    if verbose:
        print_with_prefix(prefix, message)

def verbose_with_indent(prefix, first_message, other_messages):
    if verbose:
        print_with_indent(prefix, first_message, other_messages)

def print_with_prefix(prefix, message):
    print('[{0:s}] {1}'.format(prefix, message))

def print_with_indent(prefix, first_message, other_messages):
    formatted_prefix = '[{0:s}] '.format(prefix)
    print('{0:s}{1}'.format(formatted_prefix, first_message))
    if len(other_messages) > 0:
        indent = ' ' * len(formatted_prefix)
        wrapper = textwrap.TextWrapper(
            initial_indent=indent, subsequent_indent=indent, width=70)
        for message in other_messages:
            print(wrapper.fill(message))

def run_tcp_server(local_host, local_port, remote_host, remote_port, timeout):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((local_host, local_port))
        server.listen(1)
        print_with_prefix('server', 'listening on {0:s}:{1:d}'.format(local_host, local_port))
        while True:
            print_with_prefix('server', 'waiting for connection')
            conn, addr = server.accept()
            print_with_prefix('server', 'accepted connection from: {0}'.format(addr))
            with conn:
                conn.settimeout(timeout)
                try:
                    handle_tcp_connection(conn, remote_host, remote_port, timeout)
                except OSError as msg:
                    print_with_prefix('server', 'error occured while handling connection: {0}'.format(msg))

def handle_tcp_connection(conn, remote_host, remote_port, timeout):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as remote:
        remote.settimeout(timeout)
        remote.connect((remote_host, remote_port))
        while True:
            print_with_prefix('connection', 'receive data from client')
            data = conn.recv(bufsize)
            if not data:
                print_with_prefix('connection', 'no data received from client, closing')
                break
            print_with_prefix('connection', 'received {0:d} bytes from client'.format(len(data)))
            # TODO: call fuzzer with client data
            print_with_prefix('connection', 'send data to server')
            remote.sendall(data)
            print_with_prefix('connection', 'sent {0:d} bytes to server'.format(len(data)))
            print_with_prefix('connection', 'receive data from server')
            data = remote.recv(bufsize)
            if not data:
                print_with_prefix('connection', 'no data received from server, closing')
                break
            print_with_prefix('connection', 'received {0:d} bytes from server'.format(len(data)))
            # TODO: call fuzzer with server data
            print_with_prefix('connection', 'sent {0:d} bytes to client'.format(len(data)))
            conn.sendall(data)

    print_with_prefix('connection', 'closed')

def fuzz(data):
    # do nothing so far
    return data

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
parser.add_argument('--timeout', help='Connection timeout', type=int, default=60)
parser.add_argument('--verbose', help='more logs', action='store_true', default=False)

args = parser.parse_args()

verbose = args.verbose

if args.test:
    parts = args.test.split(':')
    if len(parts) == 1:
        start_test = int(parts[0])
        end_test = start_test
    elif len(parts) == 2:
        start_test = int(parts[0])
        if parts[1] == '' or parts[1] == 'infinite':
            end_test = float('inf')
        else:
            end_test = int(parts[1])
    else:
        raise Exception('Could not parse --test value, too many colons')
else:
    start_test = 0
    end_test = float('inf')

parts = args.ratio.split(':')
if len(parts) == 1:
    min_ratio = float(parts[0])
    max_ratio = min_ratio
elif len(parts) == 2:
    min_ratio = float(parts[0])
    max_ratio = float(parts[1])
else:
    raise Exception('Could not parse --ratio value, too many colons')

if args.protocol == 'tcp':
    run_tcp_server(args.local_host, args.local_port,
                   args.remote_host, args.remote_port,
                   args.timeout)
elif args.protocol == 'udp':
    raise Exception('UDP is not supported yet')
