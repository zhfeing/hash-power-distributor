import pickle
import uuid
from tornado.iostream import IOStream


def to_byte_str(obj: object, end_with: bytes = b"") -> bytes:
    """convert a object to a string, notice all attribute must can be serialize to json"""
    return pickle.dumps(obj) + end_with


def from_byte_str(byte_str: bytes) -> object:
    """convert a string to an attribute dictionary"""
    return pickle.loads(byte_str)


async def read_until_symbol(stream: IOStream, symbol: bytes) -> bytes:
    context = await stream.read_until(symbol)
    return context[:-len(symbol)]


def bytes_to_str(s: str):
    return str(s, encoding="utf-8")


def get_uuid() -> str:
    """get uuid1 as from hex string"""
    return uuid.uuid1().hex
