from tornado.tcpclient import TCPClient
from tornado.iostream import StreamClosedError, IOStream
from tornado.ioloop import IOLoop
from tornado.netutil import Resolver
from typing import Tuple, List
import asyncio

import descriptor
import utils


class ResultTypeError(Exception):
    pass


class AllocateGpuFailed(Exception):
    pass


class Slave(TCPClient):
    def __init__(
        self,
        server_address: Tuple,
        resolver: Resolver = None
    ):
        super().__init__(resolver)
        self._server_host = server_address[0]
        self._server_port = server_address[1]
        self._loop = IOLoop.current()

    async def _connect_to_server(self) -> IOStream:
        stream = await self.connect(
            host=self._server_host,
            port=self._server_port
        )
        return stream

    async def _session(self, request: descriptor.BaseRequest) -> descriptor.BaseResult:
        stream = await self._connect_to_server()
        await stream.write(request.to_byte_str())
        result_byte = await utils.read_until_symbol(stream, descriptor.STOP_SYMBOL)
        result = descriptor.BaseResult.from_byte_str(result_byte)
        if not stream.closed():
            stream.close()
        return result

    #################################################################################
    ## requests

    async def allocate_gpus(self, num_gpus: int, exclusive: bool = False, mem_size: int = None):
        try:
            request = descriptor.Request_AllocateGpus(num_gpus, exclusive, mem_size)
            result: descriptor.Result_AllocateGpus = await self._session(request)
            if type(result) != descriptor.Result_AllocateGpus:
                raise ResultTypeError
            if not result.success:
                print("allocate failed")
            print(result)
            return result
        except StreamClosedError:
            print("[error] can not connect")

    async def get_system_info(self):
        request = descriptor.Request_GetSystemInfo()
        try:
            result: descriptor.Result_GetSystemInfo = await self._session(request)
            if type(result) != descriptor.Result_GetSystemInfo:
                raise ResultTypeError
            print(result)
        except StreamClosedError:
            print("[error] can not connect")

    async def release_gpus(self, uuids: List[str]):
        request = descriptor.Request_ReleaseGpus(uuids)
        try:
            result: descriptor.Result_ReleaseGpus = await self._session(request)
            if type(result) != descriptor.Result_ReleaseGpus:
                raise ResultTypeError
            if not result.success:
                print("release failed")
            print(result)
        except StreamClosedError:
            print("[error] can not connect")


async def main_process():
    loop = IOLoop.current()
    slave = Slave(
        server_address=("vipa-109", 13105),
    )
    await slave.get_system_info()
    # result_1 = await slave.release_gpus(["346ae89c338511ea88671831bfcc2809"])
    # result_1 = await slave.release_gpus(["346ae89c338511ea88671831bfcc2809"])
    # result_1 = await slave.allocate_gpus(num_gpus=1, exclusive=True, mem_size=10)
    # result_1 = await slave.allocate_gpus(num_gpus=1, exclusive=False, mem_size=10)
    # result_1 = await slave.allocate_gpus(num_gpus=1, exclusive=False, mem_size=100 * 1 << 20)
    # result_1 = await slave.allocate_gpus(num_gpus=1, exclusive=True, mem_size=10)
    # result_2 = await slave.allocate_gpus(num_gpus=1, exclusive=True, mem_size=10)
    # if result_1.success:
    # await slave.release_gpus(result_1.uuids)
    # result_1 = await slave.release_gpus(["613d7378335611ea88671831bfcc2809"])
    loop.stop()



if __name__ == "__main__":
    loop = IOLoop.current()
    loop.add_callback(main_process)
    loop.start()
