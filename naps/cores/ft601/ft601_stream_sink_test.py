from unittest import TestCase
from amaranth import *
from naps import CounterStreamSource, FT601StreamSink, SimPlatform, TristateIo, OutputIo, InputIo


class Ft601FakeResource:
    reset = OutputIo()
    data = TristateIo(32)
    be = TristateIo(4)
    oe = OutputIo()
    read = OutputIo()
    write = OutputIo()
    siwu = OutputIo()
    rxf = InputIo()
    txe = InputIo()
    clk = InputIo()


class TestFt601StreamSink(TestCase):
    def test_smoke(self):
        m = Module()

        platform = SimPlatform()
        platform.add_sim_clock("sync", 50e6)
        platform.add_sim_clock("ft601_outer", 100e6)

        ft601 = Ft601FakeResource()
        stream_counter = m.submodules.stream_counter = CounterStreamSource(32, count_if_not_ready=True)
        m.d.comb += ft601.clk.i.eq(ClockSignal("ft601_outer"))
        m.submodules.dut = FT601StreamSink(ft601, stream_counter.output)

        def testbench():
            read = []
            for i in range(3):
                yield ft601.txe.i.eq(1)
                written = 0
                began = False
                while True:
                    if not began:
                        if (yield ft601.write.o):
                            began = True
                    if began:
                        if (yield ft601.write.o):
                            written += 1
                            read.append((yield ft601.data.o))
                        else:
                            yield ft601.txe.i.eq(0)
                            break
                        if written == 2048:
                            yield ft601.txe.i.eq(0)
                            break
                    yield
                yield
                assert written == 2048
                for i in range(200):
                    yield
                    assert (yield ft601.write.o) == 0, "write was high in idle cycle {}".format(i)

            # validate the received data
            print(read)
            last = 0
            for v in read:
                assert v == last
                last += 1

        import sys
        sys.setrecursionlimit(1500)  # this test compiles a rather large memory and fails with the standard recursion limit
        platform.sim(m, (testbench, "ft601"))
