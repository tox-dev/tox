import signal
import sys
import time
from pathlib import Path


def handler(signum, frame):
    print("how about no signal {}".format(signum), file=sys.stdout)
    sys.stdout.flush()  # force output now before we get killed


signal.signal(signal.SIGTERM, handler)

idle_file = Path(sys.argv[1])
start_file = Path(sys.argv[2])

idle_file.write_text("")
time.sleep(float(sys.argv[3]))

while True:
    try:
        if not start_file.exists():
            start_file.write_text("")
        time.sleep(100)
    except KeyboardInterrupt:
        print("how about no KeyboardInterrupt", file=sys.stderr)
        sys.stderr.flush()  # force output now before we get killed
