import sys
import socket
from typing import Callable, List, Tuple
from configparser import ConfigParser

config = ConfigParser()
config.read_file(open('zdb.cfg'))

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        host = config.get('Settings', 'Host')
        port = config.get('Settings', 'Port')
        
        print('connecting to {} on port {}...'.format(host, port), end='', flush=True)
        sock.connect((host, int(port)))
        print('connected')
        response_handler = ServerResponseHandler(sock)
        while True:
            print('> ', end='')
            command = input()
            if command in ['quit', 'exit']:
                sys.exit()

            server_tuple_list = getServerCommand(command)
            for server_command, response_func in server_tuple_list:
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

def getServerCommand(command: str) -> List[Tuple[str, Callable[..., None]]]:
    tuple_list = []

    # special case help command (nothing sent to server)
    if command == 'help':
        print_help()
        return tuple_list
    
    split = command.split()
    # ignore empty input
    if len(split) == 0:
        return tuple_list

    if split[0] == 'break':
        func_name = split[1]
        break_addr, found_overlay = getFunctionBreakPoint(func_name)
        if break_addr is None:
            return tuple_list
        if found_overlay:
            tuple_list.append(('break {} ovl {} {}'.format(func_name, found_overlay, break_addr), ServerResponseHandler.defaultHandler))
        else:
            tuple_list.append(('break {} {}'.format(func_name, break_addr), ServerResponseHandler.defaultHandler))
    elif split[0] == 'info':
        if split[1] == 'breakpoints':
            tuple_list.append(('info breakpoints', ServerResponseHandler.defaultHandler))
    elif split[0] == 'delete':
        func_name = split[1]
        tuple_list.append(('delete {}'.format(func_name), ServerResponseHandler.defaultHandler))
    elif split[0] == 'load':
        if split[1] == 'breakpoints':
            filename = split[2]
            with open(filename) as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if line == '' or line.startswith('//'):
                        continue
                    func_name = line
                    break_addr, found_overlay = getFunctionBreakPoint(func_name)
                    if break_addr is None:
                        continue
                    if found_overlay:
                        tuple_list.append(('break {} ovl {} {}'.format(func_name, found_overlay, break_addr), ServerResponseHandler.defaultHandler))
                    else:
                        tuple_list.append(('break {} {}'.format(func_name, break_addr), ServerResponseHandler.defaultHandler))
    elif split[0] == 'clear':
        tuple_list.append(('clear', ServerResponseHandler.defaultHandler))
                        
    
    if len(tuple_list) == 0:
        print('Error: command not recognized')

    return tuple_list

# print error message and exit with error
def fail(error_msg: str):
    print(error_msg, file=sys.stderr)
    sys.exit(1)


def getFunctionBreakPoint(funcName: str) -> int:
    map_filepath = config.get('Settings', 'Map_Filepath')
    
    try:
        with open(map_filepath) as f:
            lines = f.readlines()
    except Exception:
        fail(f'Could not open {map_filepath} as a map file for reading')

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
        print(f'Error: found more than one function with name {funcName}')
        return None, found_overlay
    else:
        print(f'Error: could not find function with name {funcName}')
        return None, found_overlay

    return None, None

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
            new_data = self.sock.recv(1024).decode('utf-8')
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
        if msg != 'success':
            print('\n{}\n'.format(msg))


if __name__ == '__main__':
    main()
