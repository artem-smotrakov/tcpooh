#!/usr/bin/python

import io
import struct
import binascii
import codecs
import random
import socket
import textwrap
from enum import Enum

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

class DataDirection(Enum):
    FROM_CLIENT_TO_SERVER = 1
    FROM_SERVER_TO_CLIENT = 2

class HandlerResult:

    def __init__(self, data):
        self.data = data
        self.dropped = False
        self.reply = None

    def data(self):         return self.data
    def is_dropped(self):   return self.dropped
    def has_reply(self):    return self.reply != None
    def drop(self):         self.dropped = True

# base class for data handlers
class Handler:

    # should return true if it can handle data in specified direction
    def supports(self, direction):
        return False

    # handle data
    def handle(self, data):
        return HandlerResult(data)

    # called in the end to let a handler know that we are done
    def finalize(self):
        pass

class FtpDropAuth(Handler):

    def __init__(self):
        self.detected = False

    def supports(self, direction):
        return direction == DataDirection.FROM_CLIENT_TO_SERVER

    def handle(self, data, direction):
        result = HandlerResult(data)
        try:
            string = data.decode('utf-8')
        except Exception as err:
            self.log('could not decode FTP command, skip: {0}'.format(err))
            return result
        if 'AUTH' in string:
            self.log('drop AUTH message, return 202 Command not implemented')
            result.drop()
            result.reply = '202 Command not implemented\r\n'.encode('ascii')
        return result

    def log(self, msg):
        print_with_prefix('FtpDropAuth', msg)

class DumpMultiprocessing(Handler):

    def supports(self, direction):
        return True

    def handle(self, data, direction):
        result = HandlerResult(data)
        buf = io.BytesIO()
        buf.write(data[0:4])
        size, = struct.unpack("!i", buf.getvalue())
        self.log('size: {0}'.format(size))
        self.log('data: {0}'.format(data[4:]))
        return result

    def log(self, msg):
        print_with_prefix('DumpMultiprocessing', msg)

# gathers data, and stores it to a file when close() method is called
# it stores data in hex format
class DataDumper(Handler):

    def __init__(self, filename, direction):
        self.filename = filename
        self.direction = direction

    def supports(self, direction):
        return self.direction == direction

    def handle(self, data):
        self.data.append(data)

    # data is written to a file only when this method is called
    # it's better to  call it in finally block
    # to make sure that it always writes data to a file
    def finalize(self):
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

        if self.mode() == 'ftp_drop_auth':
            self.handlers = [ FtpDropAuth() ]
        if self.mode() == 'dump_multiprocessing':
            self.handlers = [ DumpMultiprocessing() ]
        else:
            raise Exception('Unexpected mode {0:s}'.format(self.args['mode']))

        self.server = self.create_server()

    def mode(self):
        return self.args['mode']

    def create_server(self):
        return Server(self.local_host(), self.local_port(),
                      self.remote_host(), self.remote_port(),
                      self.timeout(), self.handlers)

    def local_host(self):  return self.args['local_host']
    def local_port(self):  return self.args['local_port']
    def remote_host(self): return self.args['remote_host']
    def remote_port(self): return self.args['remote_port']
    def timeout(self):     return self.args['timeout']

    def run(self):
        try:
            self.server.start()
        finally:
            self.finalize()

    def fuzz_client(self):
        return self.args['mode'] == 'fuzz_client'

    def fuzz_server(self):
        return self.args['mode'] == 'fuzz_server'

    def finalize(self):
        for handler in self.handlers: handler.finalize()

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
# it calls handlers to process data
class Server:

    bufsize = 4096

    def __init__(self, local_host, local_port, remote_host, remote_port, timeout, handlers = []):
        self.local_host = local_host
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.timeout = timeout
        self.handlers = []
        if handlers != None:
            for handler in handlers: self.handlers.append(handler)

    # main server loop
    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.local_host, self.local_port))
            server.listen(1)
            self.log('listening on {0:s}:{1:d}'.format(self.local_host, self.local_port))
            while True:
                self.log('waiting for connection')
                conn, addr = server.accept()
                self.log('accepted connection from: {0}'.format(addr))
                with conn:
                    conn.settimeout(self.timeout)
                    try:
                        self.handle_tcp_connection(conn)
                    except OSError as msg:
                        self.log('error occured while handling connection: {0}'.format(msg))

    # handle incoming connection
    def handle_tcp_connection(self, conn):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as remote:
            remote.settimeout(self.timeout)
            remote.connect((self.remote_host, self.remote_port))
            while True:
                self.log('receive data from client')
                received = False
                try:
                    data = conn.recv(self.bufsize)
                    if not data:
                        self.log('no data received from client, closing')
                        break
                    else:
                        received = True
                except OSError as msg:
                    self.log('error occured while receiving data from client: {0}'.format(msg))

                if received:
                    self.log('received {0:d} bytes from client'.format(len(data)))
                    result = self.handle_data(data, DataDirection.FROM_CLIENT_TO_SERVER)
                    if result.is_dropped():
                        self.log('original data from client dropped')
                        if result.has_reply():
                            self.log('send modified reply back to client')
                            conn.sendall(result.reply)
                            self.log('sent {0:d} bytes to client'.format(len(result.reply)))
                            continue
                    else:
                        self.log('send data to server')
                        remote.sendall(data)
                        self.log('sent {0:d} bytes to server'.format(len(data)))

                self.log('receive data from server')
                received = False
                try:
                    data = remote.recv(self.bufsize)
                    if not data:
                        self.log('no data received from server, closing')
                        break
                    else:
                        received = True
                except OSError as msg:
                    self.log('error occured while receiving data from server: {0}'.format(msg))

                if received:
                    self.log('received {0:d} bytes from server'.format(len(data)))
                    result = self.handle_data(data, DataDirection.FROM_SERVER_TO_CLIENT)
                    if result.is_dropped():
                        self.log('original data from server dropped')
                        if result.has_reply():
                            self.log('send modified data to client')
                            conn.sendall(result.reply)
                            self.log('sent {0:d} bytes to client'.format(len(result.reply)))
                            continue
                    else:
                        self.log('send data to client')
                        conn.sendall(data)
                        self.log('sent {0:d} bytes to client'.format(len(data)))

        self.log('connection closed')

    def handle_data(self, data, direction):
        result = HandlerResult(data)
        for handler in self.handlers:
            if handler.supports(direction):
                result = handler.handle(data, direction)
                if result.is_dropped(): return result
        return result

    def log(self, msg):
        print_with_prefix('Server', msg)

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
