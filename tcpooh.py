#!/usr/bin/python

import socket
import argparse

# TODO: UDP support

# constants
bufsize = 4096

def run_tcp_server(local_host, local_port, remote_host, remote_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((local_host, local_port))
        server.listen(1)
        print('Listen on {0:s}:{1:d}'.format(local_host, local_port))
        while True:
            print('Waiting for connection')
            conn, addr = server.accept()
            print('Accepted connection from', addr)
            with conn:
                try:
                    handle_tcp_connection(conn, remote_host, remote_port)
                except OSError as msg:
                    print('Error occured while handling connection: {0:s}'.format(msg))

def handle_tcp_connection(conn, remote_host, remote_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as remote:
        remote.connect((remote_host, remote_port))
        while True:
            data = conn.recv(bufsize)
            if not data:
                break
            remote.sendall(data)
            data = remote.recv(bufsize)
            if not data:
                break
            conn.sendall(data)

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

args = parser.parse_args()

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
    run_tcp_server(args.local_host, args.local_port, args.remote_host, args.remote_port)
elif args.protocol == 'udp':
    raise Exception('UDP is not supported yet')
