#!/usr/bin/python

import socket

parser = argparse.ArgumentParser()
parser.add_argument('--local_host', help='local host name', default='localhost')
parser.add_argument('--local_port', help='local port to listen', type=int, default=10101)
parser.add_argument('--remote_host', help='remote host name', default='localhost')
parser.add_argument('--remote_port', help='remote port', type=int, default=80)
parser.add_argument('--test',
                    help='test range, it can be a number, or an interval "start:end"')
parser.add_argument('--ratio',
                    help='fuzzing ratio range, it can be a number, or an interval "start:end"',
                    default='0.01:0.05')
args = parser.parse_args()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((args.local_host, args.port))
    s.listen(1)
    conn, addr = s.accept()
    with conn:
        print('Connected by', addr)
        while True:
            data = conn.recv(4096)
            raise Exception('Not implemented')

def fuzz(data):
    # do nothing so far
    return data
