from gpu_holder import GpuHolder, CUDARuntimeError
from time import sleep
import multiprocessing


if __name__ == "__main__":
    multiprocessing.set_start_method('forkserver')

    try:
        h1 = GpuHolder(0, False)
    except CUDARuntimeError as error:
        print(error)

    try:
        h1 = GpuHolder(0, False)
    except CUDARuntimeError as error:
        print(error)
