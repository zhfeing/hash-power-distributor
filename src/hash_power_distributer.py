import os
import sys
import atexit
import time

 

async def hash_power_distributer():
    # daemon codes
    pass

 
def make_daemon(pid_file=None):
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
        # while exit remove pid file
        atexit.register(os.remove, pid_file)
    
    # run hash power distributer
    f = open("/media/Data/project/hash-power-distributor/out", "w+")
    while True:
        f.write("heart beat\n")
        time.sleep(1)
        f.flush()


if __name__ == "__main__":
    make_daemon("/media/Data/project/hash-power-distributor/hashpwd.pid")
    # daemon("/var/run/hashpwd.pid")
