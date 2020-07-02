import sys
import socket
from typing import Callable

# TODO: read from config file
HOST = '172.28.64.1'
PORT = 7340

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        print('connecting to server...', end='', flush=True)
        sock.connect((HOST, PORT))
        print('connected')
        response_handler = ServerResponseHandler(sock)
        while True:
            print('> ', end = '')
            command = input()
            if command == 'quit':
                sys.exit()

            # TODO: change to response handler
            server_command, response_func = getServerCommand(command)
            if server_command:
                sendToServer(sock, server_command)
                if response_func:
                    response_handler.handler = response_func
                    response_handler.handler(response_handler)


def sendToServer(sock, msg: str):
    msg_bytes = bytearray(msg, encoding='utf-8')
    header = bytearray(len(msg_bytes).to_bytes(4, byteorder='little', signed=False))
    server_msg = header + msg_bytes
    sock.sendall(server_msg)

def getServerCommand(command: str) -> (str, Callable[..., None]):
    server_command = None
    response_handler = None

    # special case help command (nothing sent to server)
    if command == 'help':
        print_help()
        return None, False
    
    split = command.split()
    # ignore empty input
    if len(split) == 0:
        return None, False

    if split[0] == 'break':
        func_name = split[1]
        break_addr, found_overlay = getFunctionBreakPoint(func_name)
        if found_overlay:
            server_command = 'break {} ovl {} {}'.format(func_name, found_overlay, break_addr)
        else:
            server_command = 'break {} {}'.format(func_name, break_addr)
    elif split[0] == 'info':
        if split[1] == 'breakpoints':
            server_command = 'info breakpoints'
            response_handler = ServerResponseHandler.defaultHandler
    elif split[0] == 'delete':
        func_name = split[1]
        server_command = 'delete {}'.format(func_name)
    
    
    if server_command is None:
        print('Error: command not recognized')

    return server_command, response_handler

# print error message and exit with error
def fail(error_msg: str):
    print(error_msg, file=sys.stderr)
    sys.exit(1)

#TODO: move to OOT-specific logic to own module
MAP_FILEPATH = '/home/brian/gamedev/oot/build/z64.map'

def getFunctionBreakPoint(funcName: str) -> int:
    try:
        with open(MAP_FILEPATH) as f:
            lines = f.readlines()
    except Exception:
        fail(f'Could not open {MAP_FILEPATH} as a map file for reading')

    # find function address in ROM - logic borrowed from diff.py
    cur_overlay = None
    found_overlay = None
    cands = []
    last_line = ''
    for line in lines:
        if 'load address' in line:
            tokens = last_line.split() + line.split()
            ram_base = int(tokens[1], 0)
            if tokens[0].startswith('..ovl_'):
                cur_overlay = tokens[0][6:].lower()
            else:
                cur_overlay = None
        if line.endswith(' ' + funcName + '\n'):
            ram = int(line.split()[0], 0)
            found_overlay = cur_overlay
            if found_overlay:
                offset = ram - ram_base
                cands.append(offset)
            else:
                cands.append(ram)
        last_line = line
    
    if len(cands) == 1:
        return cands[0], found_overlay
    elif len(cands) > 1:
        fail(f'Found more than one function with name {funcName}')
    else:
        fail(f'Could not find function with name {funcName}')

    return None

def print_help():
    print('\nCommands:\nbreak\t-- sets breakpoint on the given function\ndelete\t-- deletes breakpoint on the given function\ninfo breakpoints\t-- prints list of active breakpoints\n')

class ServerResponseHandler():
    def __init__(self, sock, handler=None):
        self.sock = sock
        self.handler = handler if handler else self.defaultHandler
        self.headerLen = 10

        self.resetMsg()
    
    # returns a complete string message from server
    def getFromServer(self) -> str:
        while True:
            new_data = self.sock.recv(1024).decode('ascii')
            self.charsReceived += len(new_data)
            self.responseMsg += new_data

            if not self.readHeader and self.charsReceived >= self.headerLen:
                self.charsExpected = self.headerLen + int(self.responseMsg[0:self.headerLen], 0)
                self.readHeader = True

            if self.readHeader and self.charsReceived == self.charsExpected:
                msg = self.responseMsg
                self.resetMsg()
                return msg[self.headerLen:]
            elif self.readHeader and self.charsReceived > self.charsExpected:
                fail('Error: received invalid packet')
    
    def resetMsg(self):
        self.charsReceived = 0
        self.charsExpected = -1
        self.readHeader = False
        self.responseMsg = ''

    def defaultHandler(self):
        msg = self.getFromServer()
        print('\n{}\n'.format(msg))


if __name__ == '__main__':
    main()
