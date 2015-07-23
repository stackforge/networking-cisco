#!/usr/bin/python

import sys 
from server import dfa_server as dfa


def dfa_server():
    dfa.dfa_server()

if __name__ == '__main__':
    sys.exit(dfa_server())
