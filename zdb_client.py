import sys
import os
import socket
import json

# TODO: read from config file
HOST = '172.28.224.1'
PORT = 7340

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        print('connecting to server...', end='')
        sock.connect((HOST, PORT))
        print('connected')
        addr_to_func, func_to_addr = getFunctionMaps()
        # print(addr_to_func)
        # print(func_to_addr)
        addr_to_func_data = json.dumps(addr_to_func)
        func_to_addr_data = json.dumps(func_to_addr)
        print('sending function maps to server...', end='')
        # sock.sendall(bytes(addr_to_func_data, encoding='utf-8'))
        # sock.sendall(bytes(func_to_addr_data, encoding='utf-8'))
        sendToServer(sock, addr_to_func_data)
        sendToServer(sock, func_to_addr_data)
        print('sent')
        while True:
            command = input()
            if command == 'exit':
                sys.exit()
            server_command, expect_response = getServerCommand(command)
            # send server command if applicable
            if server_command:
                # sock.sendall(server_command)
                sendToServer(sock, server_command)
                if expect_response:
                    print('\n{}\n'.format(sock.recv(8096).decode('ascii')))


def sendToServer(sock, msg: str):
    # start_str = 'START'
    # stop_str = 'STOP'

    # sock.sendall(bytes(start_str), encoding='utf-8')
    # count = len(msg.encode('utf-8'))
    count = len(msg)
    header_len = 10
    header = '0x{0:0{1}X}'.format(count, header_len - 2)
    # send header
    sock.sendall(bytes(header, encoding='utf-8'))
    # send data
    sock.sendall(bytes(msg, encoding='utf-8'))
    # sock.sendall(bytes(stop_str, encoding='utf-8'))

def getServerCommand(command: str) -> (str, bool):
    server_command = ''
    expect_response = False
    
    split = command.split()
    # ignore empty input
    if len(split) == 0:
        return None, False

    if split[0] == 'b':
        func_name = split[1]
        break_addr, found_overlay = getFunctionBreakPoint(func_name)
        if found_overlay:
            return 'b {} ovl {} {}'.format(func_name, found_overlay, break_addr), False
        else:
            return 'b {} {}'.format(func_name, break_addr), False
    elif split[0] == 'info':
        if split[1] == 'breakpoints':
            server_command = 'info breakpoints'
            expect_response = True
    elif split[0] == 'del':
        func_name = split[1]
        server_command = 'del {}'.format(func_name)
        expect_response = False
    elif split[0] == 'backtrace':
        server_command = 'backtrace'
        expect_response = True
    else:
        print('Error: command not recognized')
        return None, False

    return server_command, expect_response

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

    return None

def getFunctionMaps():
    addr_to_func = {}
    func_to_addr = {}
    
    try:
        with open(MAP_FILEPATH) as f:
            lines = f.readlines()
    except Exception:
        fail(f'Could not open {MAP_FILEPATH} as a map file for reading')

    in_text_section = False
    last_line = ''
    for line in lines:
        if 'load address' in line:
            tokens = last_line.split() + line.split()
            if tokens[0].startswith('..ovl_'):
                cur_overlay = tokens[0][6:].lower()
                ovl_ram_base = int(tokens[1], 0)
            else:
                cur_overlay = None
        
        if in_text_section:
            tokens = line.split()
            if len(tokens) == 2:
                addr = int(tokens[0], 0)
                func_name = tokens[1]
                if cur_overlay is None:
                    addr_to_func[addr] = func_name
                    func_to_addr[func_name] = addr
                # TODO: add back support for overlays
                # else:
                #     ovl_offset = addr - ovl_ram_base
                #     if cur_overlay not in addr_to_func:
                #         addr_to_func[cur_overlay] = {}
                    
                #     addr_to_func[cur_overlay][ovl_offset] = func_name
                #     func_to_addr[func_name] = (cur_overlay, ovl_offset)
            else:
                in_text_section = False
        else:
            in_text_section = line.startswith(' .text')

        last_line = line
    
    return addr_to_func, func_to_addr

if __name__ == '__main__':
    main()
