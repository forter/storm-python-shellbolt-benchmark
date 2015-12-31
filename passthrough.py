import sys

while True:
    line = sys.stdin.readline()
    if not line:
        raise Exception('Read EOF from stdin')
    print line
