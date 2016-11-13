#!/usr/bin/python

import binascii
import codecs
import random
import socket
import textwrap

# print out a message with prefix
def print_with_prefix(prefix, message):
    print('[{0:s}] {1}'.format(prefix, message))

# print out a message with specified prefix
def print_with_indent(prefix, first_message, other_messages):
    formatted_prefix = '[{0:s}] '.format(prefix)
    print('{0:s}{1}'.format(formatted_prefix, first_message))
    if len(other_messages) > 0:
        indent = ' ' * len(formatted_prefix)
        wrapper = textwrap.TextWrapper(
            initial_indent=indent, subsequent_indent=indent, width=80)
        for message in other_messages:
            print(wrapper.fill(message))

# gathers data, and stores it to a file when close() method is called
# it stores data in hex format
class DataDumper:

    def __init__(self, filename):
        self.filename = filename
        self.clear()

    def dump(self, data):
        self.data.append(data)

    def clear(self):
        self.data = []

    # data is written to a file only when this method is called
    # it's better to  call it in finally block
    # to make sure that it always writes data to a file
    def close(self):
        print_with_prefix('dumper', 'dump data to {0:s}'.format(self.filename))
        with open(self.filename, 'w') as file:
            for msg in self.data:
                hexx = binascii.hexlify(msg).decode('utf-8')
                print_with_prefix('dumper', 'store: {0}'.format(hexx))
                file.write(hexx)
                file.write('\n')

# it is called "boring" because it sends the same data to client again and again
# technically it's not a fuzzer, but it sends data generated by a fuzzer
# it reads data from a file, and return it if fuzz() method is called
# it expectes that data in a file were written by DataDumper
class BoringFuzzer:

    def __init__(self, filename):
        self.data = []
        with open(filename, 'r') as file:
            for line in file.readlines():
                line = line.rstrip()
                print_with_indent('boring fuzzer', 'read string:', [ line ])
                self.data.append(binascii.unhexlify(line))
        if len(self.data) == 0:
            raise Exception('No data loaded from {0:s}'.format(filename))
        print_with_prefix('boring fuzzer', 'loaded {0:d} messages'.format(len(self.data)))
        self.reset()

    def fuzz(self):
        print_with_prefix('boring fuzzer', 'test {0:d}'.format(self.test))

        fuzzed = self.data[self.test]

        if self.test == len(self.data) - 1:
            self.test = 0
        else:
            self.test += 1

        return fuzzed

    def reset(self):
        self.test = 0

# contains fuzzer configuration
# all parameters can be accessed as attributes
class Task:

    # read arguments returned by argparse.ArgumentParser
    def readargs(self, args):
        self.args = vars(args)

        # parse test range
        if args.test:
            parts = args.test.split(':')
            if len(parts) == 1:
                self.args['start_test'] = int(parts[0])
                self.args['end_test'] = int(parts[0])
            elif len(parts) == 2:
                self.args['start_test'] = int(parts[0])
                if parts[1] == '' or parts[1] == 'infinite':
                    self.args['end_test'] = float('inf')
                else:
                    self.args['end_test'] = int(parts[1])
            else:
                raise Exception('Could not parse --test value, too many colons')
        else:
            self.args['start_test'] = 0
            self.args['end_test'] = float('inf')

        # parse mutation ratio
        parts = args.ratio.split(':')
        if len(parts) == 1:
            self.args['min_ratio'] = float(parts[0])
            self.args['max_ratio'] = min_ratio
        elif len(parts) == 2:
            self.args['min_ratio'] = float(parts[0])
            self.args['max_ratio'] = float(parts[1])
        else:
            raise Exception('Could not parse --ratio value, too many colons')

        if self.args['mode'] == 'fuzz_client' or self.args['mode'] == 'fuzz_server':
            self.fuzzer = DumbByteArrayFuzzer(self.args['start_test'],
                                                self.args['min_ratio'],
                                                self.args['max_ratio'])
            if self.args['data']:
                self.dumper = DataDumper(self.args['data'])

                if self.args['protocol'] == 'tcp':
                    self.server = Server(self)
                else:
                    raise Exception('Unsupported protocol: {0:s}'.format(self.args['protocol']))
        elif self.args['mode'] == 'client_data':
            raise Exception('Unsupported mode: {0:s}'.format(self.args['mode']))
        elif self.args['mode'] == 'server_data':
            self.server = BoringServer(self)
        else:
            raise Exception('Unexpected mode {0:s}'.format(self.args['mode']))

    def __getattr__(self, name):
        return self.args[name]

    def run(self):
        try:
            self.server.start()
        finally:
            self.finalize()

    def fuzz_client(self):
        return self.args['mode'] == 'fuzz_client'

    def fuzz_server(self):
        return self.args['mode'] == 'fuzz_server'

    def clear_dumper(self):
        if self.dumper:
            self.dumper.clear()

    def finalize(self):
        if self.dumper:
            self.dumper.close()

# dumb fuzzer for a byte array
class DumbByteArrayFuzzer:

    def __init__(self, start_test, min_ratio, max_ratio, ignored_bytes = ()):
        self.start_test = start_test
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.ignored_bytes = ignored_bytes
        self.reset()

    def set_test(self, test):
        self.test = test

    def reset(self):
        self.test = self.start_test
        self.random_seed = random.Random()
        self.random_n = random.Random()
        self.random_position = random.Random()
        self.random_byte = random.Random()

    def fuzz(self, data):
        print_with_prefix('fuzzer', 'test {0:d}'.format(self.test))

        fuzzed = bytearray(data)
        min_bytes = int(float(self.min_ratio) * int(len(data)));
        max_bytes = int(float(self.max_ratio) * int(len(data)));

        self.random_seed.seed(self.test)
        seed = self.random_seed.random()

        if min_bytes == max_bytes:
            n = min_bytes
        else:
            self.random_n.seed(seed)
            n = self.random_n.randrange(min_bytes, max_bytes)

        self.random_position.seed(seed)
        self.random_byte.seed(seed)

        i = 0
        while (i < n):
            pos = self.random_position.randint(0, len(fuzzed) - 1)
            if self.isignored(fuzzed[pos]):
                continue
            b = self.random_byte.randint(0, 255)
            fuzzed[pos] = b
            i += 1

        self.test += 1
        return fuzzed

    def isignored(self, symbol):
        return symbol in self.ignored_bytes

# TCP server which redirects incoming connections to a remote server
# it calls a fuzzer to fuzz data from client or server
class Server:

    bufsize = 4096

    def __init__(self, task):
        self.local_host = task.local_host
        self.local_port = task.local_port
        self.remote_host = task.remote_host
        self.remote_port = task.remote_port
        self.timeout = task.timeout
        self.task = task

    # main server loop
    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.local_host, self.local_port))
            server.listen(1)
            print_with_prefix('server', 'listening on {0:s}:{1:d}'.format(self.local_host, self.local_port))
            while True:
                print_with_prefix('server', 'waiting for connection')
                conn, addr = server.accept()
                print_with_prefix('server', 'accepted connection from: {0}'.format(addr))
                with conn:
                    conn.settimeout(self.timeout)
                    try:
                        self.handle_tcp_connection(conn)
                    except OSError as msg:
                        print_with_prefix('server', 'error occured while handling connection: {0}'.format(msg))

    # handle incoming connection
    def handle_tcp_connection(self, conn):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as remote:
            remote.settimeout(self.timeout)
            remote.connect((self.remote_host, self.remote_port))
            self.task.clear_dumper()
            while True:
                print_with_prefix('connection', 'receive data from client')
                received = False
                try:
                    data = conn.recv(self.bufsize)
                    if not data:
                        print_with_prefix('connection', 'no data received from client, closing')
                        break
                    else:
                        received = True
                except OSError as msg:
                    print_with_prefix('connection', 'error occured while receiving data from client: {0}'.format(msg))

                if received:
                    print_with_prefix('connection', 'received {0:d} bytes from client'.format(len(data)))
                    if self.task.fuzzer:
                        data = self.task.fuzzer.fuzz(data)
                        if self.task.dumper:
                            self.task.dumper.dump(data)

                    print_with_prefix('connection', 'send data to server')
                    remote.sendall(data)
                    print_with_prefix('connection', 'sent {0:d} bytes to server'.format(len(data)))

                print_with_prefix('connection', 'receive data from server')
                received = False
                try:
                    data = remote.recv(self.bufsize)
                    if not data:
                        print_with_prefix('connection', 'no data received from server, closing')
                        break
                    else:
                        received = True
                except OSError as msg:
                    print_with_prefix('connection', 'error occured while receiving data from server: {0}'.format(msg))

                if received:
                    print_with_prefix('connection', 'received {0:d} bytes from server'.format(len(data)))
                    if self.task.fuzz_client():
                        data = self.task.fuzzer.fuzz(data)
                        if self.task.dumper:
                            self.task.dumper.dump(data)

                    print_with_prefix('connection', 'send data to client')
                    conn.sendall(data)
                    print_with_prefix('connection', 'sent {0:d} bytes to client'.format(len(data)))

        print_with_prefix('connection', 'closed')

# this TCP server reads data from a file, and returns it to a client
# it's called "boring" because it sends the same data to pure client again and again
class BoringServer:

    bufsize = 4096

    def __init__(self, task):
        self.local_host = task.local_host
        self.local_port = task.local_port
        self.timeout = task.timeout
        self.task = task
        self.fuzzer = BoringFuzzer(task.data)

    # main server loop
    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.local_host, self.local_port))
            server.listen(1)
            print_with_prefix('boring server', 'listening on {0:s}:{1:d}'.format(self.local_host, self.local_port))
            self.fuzzer.reset()
            while True:
                print_with_prefix('server', 'waiting for connection')
                conn, addr = server.accept()
                print_with_prefix('boring server', 'accepted connection from: {0}'.format(addr))
                with conn:
                    conn.settimeout(self.timeout)
                    try:
                        self.handle_tcp_connection(conn)
                    except OSError as msg:
                        print_with_prefix('boring server', 'error occured while handling connection: {0}'.format(msg))

    # handle incoming connection
    def handle_tcp_connection(self, conn):
        while True:
            print_with_prefix('boring connection', 'receive data from client')
            received = False
            try:
                data = conn.recv(self.bufsize)
                if not data:
                    print_with_prefix('boring connection', 'no data received from client, closing')
                    break
                else:
                    received = True
            except OSError as msg:
                print_with_prefix('boring connection', 'error occured while receiving data from client: {0}'.format(msg))

            if received:
                print_with_prefix('boring connection', 'received {0:d} bytes from client'.format(len(data)))
                print_with_prefix('boring connection', 'ignore client data')

                data = self.fuzzer.fuzz()
                print_with_prefix('boring connection', 'send data to client')
                conn.sendall(data)
                print_with_prefix('boring connection', 'sent {0:d} bytes to client'.format(len(data)))

        print_with_prefix('boring connection', 'closed')
