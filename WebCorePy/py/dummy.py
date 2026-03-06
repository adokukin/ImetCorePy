import time
import random
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs, flush=True)

def report_progress(progress):
    # TODO: decorate additionally if methods use stderr too
    eprint('{:.2f}'.format(progress))

TOTAL = 10
for i in range(TOTAL):
    report_progress(i / TOTAL)
    time.sleep(.5)
    print('Method output: {} s remaining'.format(TOTAL - i), flush=True)
    time.sleep(.5)
report_progress(1)
