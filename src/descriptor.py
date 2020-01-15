from typing import Dict, Any, List
import utils


STOP_SYMBOL = b"[STOP]"


class BaseDescriptor:
    def to_byte_str(self, end_with: bytes = STOP_SYMBOL) -> bytes:
        return utils.to_byte_str(self, end_with)

    @staticmethod
    def from_byte_str(byte_str: bytes):
        return utils.from_byte_str(byte_str)

    def __repr__(self):
        r = "{}(".format(type(self))
        for k in self.__dict__.keys():
            r += "{}: {}, ".format(k, self.__dict__[k])
        r += ")"
        return r

    def __str__(self):
        return self.__repr__()


class BaseRequest(BaseDescriptor):
    pass


class Request_AllocateGpus(BaseRequest):
    def __init__(self, num_gpus: int, exclusive: bool, mem_size: int = None):
        """
        Request: allocate gpu.
        Args:
            num_gpus: number of gpus needed
            exclusive: whether to allow others to use the gpu
            mem_size: estimate memory size you require while judging if a gpu has
        enough memory space.
        """
        self.num_gpus = num_gpus
        self.exclusive = exclusive
        self.mem_size = mem_size


class Request_ReleaseGpus(BaseRequest):
    def __init__(self, uuids: List[int]):
        self.uuids = uuids


class Request_GetSystemInfo(BaseRequest):
    pass


class BaseResult(BaseDescriptor):
    pass


class Result_AllocateGpus(BaseResult):
    def __init__(self, success: bool, allocated_gpus: List[int], process_pids: List[int], uuids: List[str]):
        self.success = success
        self.allocated_gpus = allocated_gpus
        self.process_pids = process_pids
        self.uuids = uuids


class Result_GetSystemInfo(BaseResult):
    def __init__(self, info: Dict[str, Any]):
        self.info = info


class Result_ReleaseGpus(BaseResult):
    def __init__(self, success: bool, failed_uuids: List[int]):
        self.success = success
        self.failed_uuids = failed_uuids

