from multiprocessing import Pipe, Process
from nmigen import Fragment, Module, DomainRenamer
from nmigen.sim import Passive

from naps import SimPlatform
from ... import *

__all__ = ["SimSocPlatform"]


class SimSocPlatform(SocPlatform):
    base_address = Address(0, 0, 0xFFFF_FFFF * 8)
    pydriver_memory_accessor = ""  # we have the real memory accessor down in the add_driver method
    csr_domain = "axi_lite"

    def __init__(self, platform):
        assert isinstance(platform, SimPlatform)
        super().__init__(platform)

        def peripherals_connect_hook(platform, top_fragment: Fragment, sames):
            from naps.cores.axi import AxiEndpoint, AxiLitePeripheralConnector

            if platform.peripherals:
                m = Module()
                platform.add_sim_clock("axi_lite", 10e6)
                axi_lite_master = AxiEndpoint(addr_bits=32, data_bits=32, lite=True)
                self.axi_lite_master = axi_lite_master

                aggregator = PeripheralsAggregator()
                for peripheral in platform.peripherals:
                    aggregator.add_peripheral(peripheral)
                connector = DomainRenamer(self.csr_domain)(AxiLitePeripheralConnector(aggregator))
                m.d.comb += axi_lite_master.connect_downstream(connector.axi)
                m.submodules.connector = connector

                platform.to_inject_subfragments.append((m, self.csr_domain))
        self.prepare_hooks.append(peripherals_connect_hook)

    def pack_bitstream_fatbitstream(self, builder):
        self.driver = builder.context.self_extracting_blobs['pydriver.py']

    def add_driver(self, driver):
        def driver_process(conn):
            class SimMemAccessor:
                base = 0

                def read(self, offset):
                    conn.send(('read', offset))
                    return conn.recv()

                def write(self, offset, to_write):
                    conn.send(('write', offset, to_write))

            g = {}
            exec(self.driver, g, g)
            Design = g["Design"]
            design = Design(SimMemAccessor())
            d = driver(design)
            response = None
            while True:
                try:
                    cmd = d.send(response)
                    conn.send(('nmigen', cmd))
                    response = conn.recv()
                except StopIteration:
                    break
            conn.send(("exit", ))
            conn.close()


        def driver_coroutine():
            from naps import axil_read, axil_write
            conn, child_conn = Pipe()
            p = Process(target=driver_process, args=(child_conn,))
            p.start()

            while True:
                if not conn.closed:
                    data = conn.recv()
                    assert isinstance(data, tuple), data
                    cmd, *rest = data
                    if cmd == "exit":
                        conn.close()
                        p.join()
                        yield Passive()
                    elif cmd == "read":
                        address, = rest
                        result = (yield from axil_read(self.axi_lite_master, address))
                        conn.send(result)
                    elif cmd == "write":
                        address, data = rest
                        yield from axil_write(self.axi_lite_master, address, data)
                    elif cmd == 'nmigen':
                        payload, = rest
                        conn.send((yield payload))
                    else:
                        raise TypeError(f"unsupported command: {cmd}")
                else:
                    yield
        self.add_process(driver_coroutine, "axi_lite")
