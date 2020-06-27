import sys
import os
import socket

# TODO: read from config file
HOST = '172.27.48.1'
PORT = 7340

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print('connected to server')
        while True:
            command = input()
            if command == 'exit':
                sys.exit()
            server_command, expect_response = getServerCommand(command)
            # send server command if applicable
            if server_command:
                sock.sendall(server_command.encode('ascii'))
                if expect_response:
                    print('\n{}\n'.format(sock.recv(1024).decode('ascii')))


def getServerCommand(command: str):
    split = command.split()
    if split[0] == 'b':
        func_name = split[1]
        break_addr, found_overlay = getFunctionBreakPoint(func_name)
        if found_overlay:
            return 'b {} ovl {} {}'.format(func_name, found_overlay, break_addr), False
        else:
            return 'b {} {}'.format(func_name, break_addr), False
    elif split[0] == 'info':
        if split[1] == 'breakpoints':
            return 'info breakpoints', True

# print error message and exit with error
def fail(error_msg: str):
    print(error_msg, file=sys.stderr)
    sys.exit(1)

#TODO: move to OOT-specific logic to own module
# OOT_DIRPATH = '/home/brian/gamedev/oot'
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
        if found_overlay:
            return cands[0], found_overlay
        else:
            return cands[0], found_overlay
    elif len(cands) > 1:
        fail(f'Found more than one function with name {funcName}')
    else:
        fail(f'Could not find function with name {funcName}')

    return 0x0

if __name__ == '__main__':
    main()
