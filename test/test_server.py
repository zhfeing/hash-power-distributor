import multiprocessing
from tornado.ioloop import IOLoop
from server import HashPowerDistributer


if __name__ == "__main__":
    multiprocessing.set_start_method('forkserver')
    server = HashPowerDistributer(logger_path="./")
    server.listen(12000, "localhost")
    IOLoop.current().start()
