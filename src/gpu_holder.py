import cupy
import traceback
import time
from multiprocessing import Process, Pipe, Value
from ctypes import c_bool


ALLOC_PERCENTAGE = 0.7


class CUDARuntimeError(Exception):
    def __init__(self, gpu_index: int, error: cupy.cuda.runtime.CUDARuntimeError, tb: str):
        self.gpu_index = gpu_index
        self.error = error
        self.tb = tb

    def __repr__(self):
        return "Exception: CUDARuntimeError(\n\tgpu_index: {},\n\terror: {}\n\ttb: {})".format(
            self.gpu_index,
            self.error,
            self.tb
        )

    def __str__(self):
        return self.__repr__()


# helper classes
class GpuHolder(Process):
    """
    When created, run a tiny program on given gpu for holding this gpu.

    Args:
        index: index of gpu you want to hold
        exclusive: whether hold gpu in exclusive mode. If `True`, cooridnating with nvml
    calculate mode `NVML_COMPUTEMODE_EXCLUSIVE_PROCESS`, create a process will prevent
    other process using this gpu by running a tiny process. If `False`, allocate memory
    for holding this gpu.
    """
    def __init__(self, index: int, exclusive: bool = False):
        super().__init__(
            target=self.hold_gpu,
            name="gpu holder process"
        )
        self._index = index
        self._exclusive = exclusive
        self._pipe_i, self._pipe_o = Pipe()
        self._exception_pipe_i, self._exception_pipe_o = Pipe()
        self._alloc_success = Value(c_bool, False)
        self.start()
        self._wait_until_alloc_success()


    def __repr__(self):
        return "GpuHolder(index: {}, exclusive: {}, is_alive: {})".format(
            self._index,
            self._exclusive,
            self.is_alive()
        )

    def __str__(self):
        return self.__repr__()

    def _wait_until_alloc_success(self):
        while True:
            # check error
            if self._exception_pipe_o.poll():
                error, tb = self._exception_pipe_o.recv()
                self.terminate()
                raise CUDARuntimeError(self._index, error, tb)

            with self._alloc_success.get_lock():
                done = self._alloc_success.value
            if done:
                break
            time.sleep(1e-3)

    def stop(self):
        self._pipe_i.send(0)
        self.join()

    @property
    def exclusive(self) -> bool:
        return self._exclusive

    @property
    def index(self) -> int:
        return self._index

    def hold_gpu(self):
        """
        Gpu holder process.

        Handle exceptions:
            cupy.cuda.runtime.CUDARuntimeError
        """
        try:
            device = cupy.cuda.Device(self._index)
            free_mem, total_mem = device.mem_info

            # allocate memory for holding this gpu
            if not self._exclusive:
                with device:
                    alloc_size = int(free_mem * ALLOC_PERCENTAGE)
                    cupy.cuda.alloc(alloc_size)
        except cupy.cuda.runtime.CUDARuntimeError as error:
            tb = traceback.format_exc()
            self._exception_pipe_i.send((error, tb))
            return

        # allocation successful
        with self._alloc_success.get_lock():
            self._alloc_success.value = True
        # wait until get receiver
        self._pipe_o.recv()

