import pynvml as nvml
import ssl
import os
import asyncio
import traceback
from typing import Dict, Any, Union, Tuple, List
from tornado.tcpserver import TCPServer
from tornado.iostream import IOStream, StreamClosedError
from tornado.ioloop import IOLoop

import descriptor
import utils
from gpu_holder import GpuHolder, CUDARuntimeError


GPU_IDLE_THRESHOLD = 0.7


# helper functions
def _no_running_processes(handle: nvml.c_nvmlDevice_t) -> bool:
    return len(nvml.nvmlDeviceGetComputeRunningProcesses(handle)) == 0


def _enough_memory(handle: nvml.c_nvmlDevice_t, mem_size: int) -> bool:
    mem_info = nvml.nvmlDeviceGetMemoryInfo(handle)
    if mem_size is not None:
        return mem_info.free > mem_size
    else:
        return mem_info.free / mem_info.total > GPU_IDLE_THRESHOLD


def _device_in_default_model(handle: nvml.c_nvmlDevice_t) -> bool:
    return nvml.nvmlDeviceGetComputeMode(handle) == nvml.NVML_COMPUTEMODE_DEFAULT


class GPUHolderProcessNotStartedError(Exception):
    pass


class HashPowerDistributer(TCPServer):
    """Hash power distributer"""
    def __init__(
        self,
        logger_path: str = "/var/log/hashpwd/",
        ssl_options: Union[Dict[str, Any], ssl.SSLContext] = None,
        max_buffer_size: int = None,
        read_chunk_size: int = None,
    ):
        super().__init__(ssl_options, max_buffer_size, read_chunk_size)
        self._despatch_task_map = {
            descriptor.Request_AllocateGpus: self._allocate_gpus,
            descriptor.Request_GetSystemInfo: self._get_system_info,
            descriptor.Request_ReleaseGpus: self._release_gpus
        }
        self._io_loop = IOLoop.current()
        self._gpu_usage_db: Dict[str, GpuHolder] = dict()

        if not os.path.isdir(logger_path):
            os.makedirs(logger_path)
        self._logger_file = open(os.path.join(logger_path, "hashpwd.log"), "w")
        # initial nvml
        try:
            nvml.nvmlInit()
        except nvml.NVMLError as error:
            self._handle_nvml_error(error, traceback.format_exc())
        # reset all gpu settings
        self._reset_all_gpus()
        # start daemon
        self._io_loop.add_callback(self._daemon)

    ######################################################################################
    # auxillary functions

    def _log(self, text: str):
        self._logger_file.write(text + "\n")
        self._logger_file.flush()

    def _log_exception(self, error: Exception, tb: str):
        self._log("[error] {},\ntraceback: \n{}".format(error, tb))

    def _set_gpu_compute_mode(self, index: int, compute_mode=nvml.NVML_COMPUTEMODE_DEFAULT):
        handle = nvml.nvmlDeviceGetHandleByIndex(index)
        if nvml.nvmlDeviceGetComputeMode(handle) != compute_mode:
            self._log("[info] gpu compute mode set to {}".format(compute_mode))
            nvml.nvmlDeviceSetComputeMode(handle, compute_mode)

    def _handle_nvml_error(self, error: nvml.NVMLError, tb: str):
        self._log_exception(error, tb)
        if error.value != nvml.NVML_ERROR_NO_PERMISSION:
            self._log("[error] Critical error happened, shuting down...")
            self.clean_up()

    def _reset_all_gpus(self):
        """
        Reset all gpu compute mode.

        Handle exceptions:
            `NVMLError`
        """
        for index in range(nvml.nvmlDeviceGetCount()):
            try:
                self._set_gpu_compute_mode(index)
            except nvml.NVMLError as error:
                self._handle_nvml_error(error, traceback.format_exc())

    def _gpu_in_use(self, index):
        """Check if given gpu has workers registered in self._gpu_usage_db"""
        in_use = False
        for holder in self._gpu_usage_db.values():
            if holder.index == index:
                in_use = True
                break
        return in_use

    def _get_idle_gpus(self, exclusive: bool, mem_size: int) -> List[int]:
        """
        Get list of idle gpus.

        Possible exceptions:
            `NVMLError`
        """
        gpu_count = nvml.nvmlDeviceGetCount()
        idle_gpus = list()

        for i in range(gpu_count):
            handle = nvml.nvmlDeviceGetHandleByIndex(i)
            if exclusive:
                no_running = _no_running_processes(handle)
                no_future_running = not self._gpu_in_use(i)
                enough_mem = _enough_memory(handle, mem_size)
                if no_running and no_future_running and enough_mem:
                    idle_gpus.append(i)
            else:
                if _enough_memory(handle, mem_size) and _device_in_default_model(handle):
                    idle_gpus.append(i)

        return idle_gpus

    def _allocate_gpu(self, index: int, exclusive: bool) -> str:
        """
        Allocate idle gpu. When `exclusive` is True, modify gpu compute mode to `EXCLUSIVE_PROCESS`.

        Return:
        Allocated gpu holder uuid as string.

        Possible exceptions:
            `NVMLError`, `CUDARuntimeError`
        """
        if exclusive:
            self._set_gpu_compute_mode(index, nvml.NVML_COMPUTEMODE_EXCLUSIVE_PROCESS)
        uuid = utils.get_uuid()
        self._gpu_usage_db[uuid] = GpuHolder(index, exclusive)
        return uuid

    def _release_gpu(self, uuid: str, handle_NVMLError: bool = False):
        """
        Release GpuHolder and set gpu compute mode to default.

        Args:
            handle_NVMLError: whether to handle NVMLError, if handle it, server will 
        decide whether to clean up based on `self._handle_nvml_error`.

        Possible exceptions:
            `NVMLError`
        """
        try:
            self._gpu_usage_db[uuid].stop()
            # clear exclusive flag
            self._set_gpu_compute_mode(self._gpu_usage_db[uuid].index, nvml.DEFAULT_MODE)
            self._gpu_usage_db.pop(uuid)
        except nvml.NVMLError as error:
            if not handle_NVMLError:
                raise error
            self._handle_nvml_error(error, traceback.format_exc())

    async def _daemon(self):
        """
        Server daemon callback.

        Handle exceptions:
            `NVMLError`
        """
        self._log("[info] server daemon started")
        while True:
            self._log("[debug] Server Daemon heart beat, {}".format(self._gpu_usage_db))
            # check whether gpu holders are alive
            for uuid in list(self._gpu_usage_db.keys()):
                if not self._gpu_usage_db[uuid].is_alive():
                    self._log("[warning] GpuHolder: {} with pid: {} was terminated unexpectedly.".format(
                        self._gpu_usage_db[uuid],
                        self._gpu_usage_db[uuid].pid
                    ))
                    if self._gpu_usage_db[uuid].exclusive:
                        try:
                            self._set_gpu_compute_mode(self._gpu_usage_db[uuid].index)
                        except nvml.NVMLError as error:
                            self._handle_nvml_error(error, traceback.format_exc())
                    self._gpu_usage_db.pop(uuid)
            await asyncio.sleep(5)

    ######################################################################################
    # descriptor handlers

    def _allocate_gpus(self, desc: descriptor.Request_AllocateGpus, stream: IOStream):
        """
        Get gpu number wanted to allocate from descriptor and try to allocate them,
        and finally send result back to requester.

        Handle exceptions:
            `NVMLError`, `CUDARuntimeError`

        Possible exceptions:
            `GPUHolderProcessNotStartedError`
        """
        # check whether has enough gpus
        success = False

        # records
        wanted_gpus: List[int] = list()
        process_pids: List[int] = list()
        uuids: List[str] = list()

        try:
            idle_gpus = self._get_idle_gpus(desc.exclusive, desc.mem_size)
            if len(idle_gpus) < desc.num_gpus:
                success = True
                return descriptor.Result_AllocateGpus(False, list(), list(), list())

            wanted_gpus = idle_gpus[: desc.num_gpus]

            # allocate gpus
            for i in wanted_gpus:
                uuid = self._allocate_gpu(i, desc.exclusive)
                uuids.append(uuid)
                if self._gpu_usage_db[uuid].pid is None:
                    raise GPUHolderProcessNotStartedError
                process_pids.append(self._gpu_usage_db[uuid].pid)

            success = True
            return descriptor.Result_AllocateGpus(True, wanted_gpus, process_pids, uuids)

        except nvml.NVMLError as error:
            self._log_exception(error, traceback.format_exc())
            return descriptor.Result_AllocateGpus(False, list(), list(), list())
        except CUDARuntimeError as error:
            self._log_exception(error, traceback.format_exc())
            return descriptor.Result_AllocateGpus(False, list(), list(), list())
        finally:
            if not success:
                # clean up allocated gpus
                for uuid in uuids:
                    self._release_gpu(uuid, handle_NVMLError=True)

    def _release_gpus(self, desc: descriptor.Request_ReleaseGpus, stream: IOStream):
        """
        Release gpu holders in given request.

        Handle exceptions:
            `NVMLError`
        """
        result = descriptor.Result_ReleaseGpus(True, list())
        for uuid in desc.uuids:
            if uuid in list(self._gpu_usage_db.keys()):
                try:
                    self._release_gpu(uuid)
                except nvml.NVMLError as error:
                    self._log("[error] while trying to release {}".format(self._gpu_usage_db[uuid]))
                    self._log_exception(error, traceback.format_exc())
                    result.success = False
                    result.failed_uuids.append(uuid)
            else:
                result.success = False
                result.failed_uuids.append(uuid)
        return result

    def _get_system_info(self, desc: descriptor.Request_GetSystemInfo, stream: IOStream):
        """
        Get system infomation.

        Handle exceptions:
            `NVMLError`
        """
        try:
            info = dict(
                driver_version=utils.bytes_to_str(nvml.nvmlSystemGetDriverVersion()),
                device_num=nvml.nvmlDeviceGetCount(),
            )
            result = descriptor.Result_GetSystemInfo(info)
            return result

        except nvml.NVMLError as error:
            self._log("[error] {}".format(error))
            return descriptor.Result_GetSystemInfo(dict())

    ######################################################################################
    ## iostream handler

    async def handle_stream(self, stream: IOStream, address: Tuple[str, int]):
        """
        Handle request of a slave, coroutine of main event loop.

        Handle exceptions:
            `StreamClosedError`
        """
        try:
            self._log("[info] get access from {}:{}".format(*address))
            descriptor_bytes = await stream.read_until(descriptor.STOP_SYMBOL)
            desc = utils.from_byte_str(descriptor_bytes)
            # deal with descriptor
            result_desc = self._despatch_task_map[type(desc)](desc, stream)
            # write result
            await stream.write(result_desc.to_byte_str())
            # close connection
            stream.close()
        except StreamClosedError as error:
            self._log("[error] connection from {}:{} is closed unexpectedly".format(*address))
            self._log_exception(error, traceback.format_exc())

    def clean_up(self):
        """
        Clean up all running jobs and exit.

        Handle exceptions:
            `NVMLError`
        """
        try:
            for uuid in list(self._gpu_usage_db.keys()):
                self._release_gpu(uuid)
            nvml.nvmlShutdown()
        except nvml.NVMLError as error:
            self._log_exception(error, traceback.format_exc())
        finally:
            self._logger_file.close()
            self._io_loop.stop()






