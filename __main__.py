#!/usr/bin/env python3
from .aduc_upload import cmdline

if __name__=='__main__':
    import sys
    sys.exit(cmdline(sys.argv[1:]))