from tornado.tcpclient import TCPClient
from tornado.iostream import StreamClosedError, IOStream
from tornado.ioloop import IOLoop
from tornado.netutil import Resolver
from typing import Tuple, List
import asyncio
from functools import partial

import descriptor
import utils


class ResultTypeError(Exception):
    pass


class AllocateGpuFailed(Exception):
    pass


class HashPowerClient(TCPClient):
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
    ## async requests

    async def async_allocate_gpus(self, num_gpus: int, exclusive: bool = False, mem_size: int = None):
        try:
            request = descriptor.Request_AllocateGpus(num_gpus, exclusive, mem_size)
            result: descriptor.Result_AllocateGpus = await self._session(request)
            if type(result) != descriptor.Result_AllocateGpus:
                raise ResultTypeError
            if not result.success:
                print("allocate failed")
            return result
        except StreamClosedError:
            print("[error] can not connect")

    async def async_get_system_info(self):
        request = descriptor.Request_GetSystemInfo()
        try:
            result: descriptor.Result_GetSystemInfo = await self._session(request)
            if type(result) != descriptor.Result_GetSystemInfo:
                raise ResultTypeError
            return result
        except StreamClosedError:
            print("[error] can not connect")

    async def async_release_gpus(self, uuids: List[str]):
        request = descriptor.Request_ReleaseGpus(uuids)
        try:
            result: descriptor.Result_ReleaseGpus = await self._session(request)
            if type(result) != descriptor.Result_ReleaseGpus:
                raise ResultTypeError
            if not result.success:
                print("release failed")
            return result
        except StreamClosedError:
            print("[error] can not connect")

    #################################################################################
    ## sync requests
    def allocate_gpus(self, num_gpus: int, exclusive: bool = False, mem_size: int = None):
        result = self._loop.run_sync(partial(self.async_allocate_gpus, num_gpus, exclusive, mem_size))
        return result

    def get_system_info(self):
        result = self._loop.run_sync(self.async_get_system_info)
        return result

    def release_gpus(self, uuids: List[str]):
        result = self._loop.run_sync(partial(self.async_release_gpus, uuids))
        return result

