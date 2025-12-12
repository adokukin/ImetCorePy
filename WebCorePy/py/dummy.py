import time
import random
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def report_progress(progress):
    # TODO: decorate additionally if methods use stderr too
    eprint('{:.2f}'.format(progress))

TOTAL = 10
for i in range(TOTAL):
    report_progress(i / TOTAL)
    time.sleep(.5)
    if random.random() > .5:
        print('Method output: {} s remaining'.format(TOTAL - i))
    time.sleep(.5)
report_progress(1)
