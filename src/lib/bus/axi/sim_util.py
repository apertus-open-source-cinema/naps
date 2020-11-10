from lib.bus.axi.axi_endpoint import Response
from lib.bus.stream.sim_util import write_to_stream, read_from_stream


def axil_read(axi, addr):
    yield from write_to_stream(axi.read_address, payload=addr)
    value, response = (yield from read_from_stream(axi.read_data, extract=("payload", "resp")))
    assert Response.OKAY.value == response
    return value


def axil_write(axi, addr, data):
    yield from write_to_stream(axi.write_address, payload=addr)
    yield from write_to_stream(axi.write_data, payload=data)
    response = (yield from read_from_stream(axi.write_response, extract="resp"))
    assert Response.OKAY.value == response
