from collections import defaultdict
from typing import Dict

from nmigen.sim import Passive
from naps import SimPlatform, write_to_stream, read_from_stream
from .axi_endpoint import AxiEndpoint, AxiResponse, AxiBurstType

__all__ = ["axil_read", "axil_write", "answer_read_burst", "answer_write_burst", "axi_ram_sim_model"]


def axil_read(axi, addr, timeout=100):
    yield from write_to_stream(axi.read_address, payload=addr)
    value, response = (yield from read_from_stream(axi.read_data, extract=("payload", "resp"), timeout=timeout))
    assert AxiResponse.OKAY.value == response
    return value


def axil_write(axi, addr, data, timeout=100):
    yield from write_to_stream(axi.write_address, payload=addr)
    yield from write_to_stream(axi.write_data, payload=data)
    response = (yield from read_from_stream(axi.write_response, extract="resp", timeout=timeout))
    assert AxiResponse.OKAY.value == response


def answer_read_burst(axi: AxiEndpoint, memory: Dict[int, int], timeout=100):
    addr, burst_len, burst_type, beat_size_bytes = yield from read_from_stream(axi.read_address, ("payload", "burst_len", "burst_type", "beat_size_bytes"), timeout)
    assert 2 ** beat_size_bytes == axi.data_bytes
    assert burst_type == AxiBurstType.INCR.value
    print("read", addr, burst_len)

    for i in range(burst_len + 1):
        yield from write_to_stream(axi.read_data, payload=memory[addr + (i * axi.data_bytes)], resp=AxiResponse.OKAY, last=(i == burst_len), timeout=timeout)


def answer_write_burst(axi: AxiEndpoint, timeout=100):
    memory = {}
    addr, burst_len, burst_type, beat_size_bytes = yield from read_from_stream(axi.write_address, ("payload", "burst_len", "burst_type", "beat_size_bytes"), timeout)
    assert 2 ** beat_size_bytes == axi.data_bytes
    assert burst_type == AxiBurstType.INCR.value
    accepted = 0
    for i in range(burst_len + 1):
        value, last, byte_strobe = yield from read_from_stream(axi.write_data, ("payload", "last", "byte_strobe"), timeout)
        if i == burst_len:
            assert last
        else:
            pass
            assert not last
        if byte_strobe != 0:
            memory[addr + i * axi.data_bytes] = value
            accepted += 1
    write_to_stream(axi.write_response, resp=AxiResponse.OKAY)
    print("wrote", memory)

    return memory, accepted


def axi_ram_sim_model(platform: SimPlatform, domain="sync"):
    mem = defaultdict(int)

    axi_writer_port = AxiEndpoint(addr_bits=32, data_bits=64, lite=False, id_bits=12)
    axi_reader_port = AxiEndpoint(addr_bits=32, data_bits=64, lite=False, id_bits=12)

    def writer_port_process():
        yield Passive()
        while True:
            memory, accepted = yield from answer_write_burst(axi_writer_port, timeout=-1)
            mem.update(memory)
    platform.add_process(writer_port_process, domain)

    def reader_port_process():
        yield Passive()
        while True:
            yield from answer_read_burst(axi_reader_port, mem, timeout=-1)
    platform.add_process(reader_port_process, domain)

    return axi_writer_port, axi_reader_port
