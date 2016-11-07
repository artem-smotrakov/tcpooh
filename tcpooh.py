#!/usr/bin/python

import socket
import argparse
import textwrap
import helper

# TODO: UDP support

class Server:

    bufsize = 4096

    def __init__(self, config, client_fuzzer = None, server_fuzzer = None):
        self.local_host = config.local_host
        self.local_port = config.local_port
        self.remote_host = config.remote_host
        self.remote_port = config.remote_port
        self.timeout = config.timeout
        self.client_fuzzer = client_fuzzer
        self.server_fuzzer = server_fuzzer

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.local_host, self.local_port))
            server.listen(1)
            helper.print_with_prefix('server', 'listening on {0:s}:{1:d}'.format(self.local_host, self.local_port))
            while True:
                helper.print_with_prefix('server', 'waiting for connection')
                conn, addr = server.accept()
                helper.print_with_prefix('server', 'accepted connection from: {0}'.format(addr))
                with conn:
                    conn.settimeout(self.timeout)
                    try:
                        self.handle_tcp_connection(conn)
                    except OSError as msg:
                        helper.print_with_prefix('server', 'error occured while handling connection: {0}'.format(msg))

    def handle_tcp_connection(self, conn):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as remote:
            remote.settimeout(self.timeout)
            remote.connect((self.remote_host, self.remote_port))
            while True:
                helper.print_with_prefix('connection', 'receive data from client')
                received = False
                try:
                    data = conn.recv(self.bufsize)
                    if not data:
                        helper.print_with_prefix('connection', 'no data received from client, closing')
                        break
                    else:
                        received = True
                except OSError as msg:
                    helper.print_with_prefix('connection', 'error occured while receiving data from client: {0}'.format(msg))

                if received:
                    helper.print_with_prefix('connection', 'received {0:d} bytes from client'.format(len(data)))
                    if self.client_fuzzer:
                        data = self.client_fuzzer.next(data)
                        helper.print_with_prefix('connection', 'send fuzzed data to server')
                    else:
                        helper.print_with_prefix('connection', 'send data to server')

                    remote.sendall(data)
                    helper.print_with_prefix('connection', 'sent {0:d} bytes to server'.format(len(data)))

                helper.print_with_prefix('connection', 'receive data from server')
                received = False
                try:
                    data = remote.recv(self.bufsize)
                    if not data:
                        helper.print_with_prefix('connection', 'no data received from server, closing')
                        break
                    else:
                        received = True
                except OSError as msg:
                    helper.print_with_prefix('connection', 'error occured while receiving data from server: {0}'.format(msg))

                if received:
                    helper.print_with_prefix('connection', 'received {0:d} bytes from server'.format(len(data)))
                    if self.server_fuzzer:
                        data = self.server_fuzzer.next(data)
                        helper.print_with_prefix('connection', 'send fuzzed data to client')
                    else:
                        helper.print_with_prefix('connection', 'send data to client')

                    conn.sendall(data)
                    helper.print_with_prefix('connection', 'sent {0:d} bytes to client'.format(len(data)))

        helper.print_with_prefix('connection', 'closed')

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
    server = Server(config, client_fuzzer, server_fuzzer)
    server.start()
elif config.protocol == 'udp':
    raise Exception('UDP is not supported yet')
