#!/usr/bin/python

import sys 

from oslo.config import cfg
from dfa.agent import dfa_agent as dfa


def dfa_agent():
    dfa.main()

if __name__ == '__main__':
    sys.exit(dfa_agent())
