#!/usr/bin/env python
import sys

try:
    password=sys.argv[1]
    print ','.join(str(ord(i)) for i in password)
except Exception as e:
    print "usage: python make_password.py mypass\nreturns ascii representation of your password"
