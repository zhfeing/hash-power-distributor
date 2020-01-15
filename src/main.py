import os
import sys
import atexit
import multiprocessing
import argparse
from tornado.ioloop import IOLoop
from server import HashPowerDistributer


def make_daemon(host, port, pid_file=None):
    """
    Create daemon process
    Args:
        pid_file: pid file of process id
    """
    pid = os.fork()
    if pid:
        sys.exit(0)

    # convert to root directory
    os.chdir('/')
    os.umask(0)
    os.setsid()

    # fork for second time, create grandson process and kill son process
    _pid = os.fork()
    if _pid:
        sys.exit(0)

    # for now, grandson process has become daemon process

    sys.stdout.flush()
    sys.stderr.flush()

    with open('/dev/null') as read_null, open('/dev/null', 'w') as write_null:
        os.dup2(read_null.fileno(), sys.stdin.fileno())
        os.dup2(write_null.fileno(), sys.stdout.fileno())
        os.dup2(write_null.fileno(), sys.stderr.fileno())

    # write pid file
    if pid_file:
        with open(pid_file, 'w+') as f:
            f.write(str(os.getpid()))
        # remove pid file while exiting
        atexit.register(os.remove, pid_file)

    # run ioloop
    server = HashPowerDistributer(logger_path="/var/log/hashpwd/")
    server.listen(port, host)
    IOLoop.current().start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid_filepath", type=str)
    parser.add_argument("--port", type=int, default=13105)
    parser.add_argument("--host", type=str, default="localhost")
    args = parser.parse_args()

    multiprocessing.set_start_method('forkserver')
    make_daemon(
        host=args.host,
        port=args.port,
        pid_file=args.pid_filepath
    )
