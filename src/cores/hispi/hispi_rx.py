from nmigen.compat import *
from nmigen.compat.genlib.cdc import MultiReg
from math import ceil

from operator import inv


# TODO(robin): implement migen support for indexed part select
#              (data[offset +: width] where offset can be a Signal)


default_config = {
    "hispi_bits": 12,
    "input_bits": 6,
    "buffersize": 5,
    "output_bits": 8,
    "num_lanes": 4,
    "lane_inversion_map": [inv, inv, inv, inv],
    "sync_lane": 0,
    "padding_size": 32
}


class HispiConfig():
    config = {}

    def __init__(self, config):
        self.config = config

    def __getattr__(self, name):
        return self.config[name]

    def __getitem__(self, name):
        return self.config[name]


def hispi_config(**configs):
    for k, v in default_config.items():
        if k not in configs:
            configs[k] = v

    return HispiConfig(configs)


class HispiBase(Module):
    def __init__(self, config):
        self.config = config


def hispi_module(cls):
    class HispiModule(cls):
        def __init__(self, config=hispi_config(), **kwargs):
            super(cls, self).__init__(config)
            super().__init__(**kwargs)

    return HispiModule


class Buffer(Module):
    def __init__(self, word_size, word_count, data_in=None, reset=None):
        if reset is None:
            reset = 2 ** (word_size * word_count) - 1

        self.word_size = word_size
        self.word_count = word_count

        self.data = Signal(self.word_size * self.word_count, reset=reset)

        if data_in is not None:
            # TODO(robin): What is better, shifting or assignment?
            # self.sync += [self[i].eq(self[i + 1]) for i in range(size - 1)]
            self.sync += self.data[:-word_size].eq(self.data[word_size:])
            #
            #            self.sync += self.data.eq(self.data >> self.word_size)
            self.sync += self.last().eq(data_in)

    #            self.sync += [self[i].eq(self[i + 1]) for i in range(word_count - 1)]
    #            self.sync += self[word_count - 1].eq(data_in)

    def slice(self, start, length):
        if type(start) is int:
            return self.data[start:start + length]
        else:
            return self.data.part(start, length)

    #            return (self.data >> start)[:length]

    def __getitem__(self, key):
        return self.data[self.word_size * key:self.word_size * (key + 1)]

    def last(self):
        return self[self.word_count - 1]


@hispi_module
class HispiBuffer(HispiBase):
    def __init__(self, data_in=None):
        buf = self.buf = self.submodules.buf = Buffer(word_count=self.config.buffersize,
                     word_size=self.config.hispi_bits,
                     data_in=data_in)

        self.word_offset = Signal(bits_for(self.config.buffersize * self.config.hispi_bits))
        self.bit_offset = Signal(bits_for(self.config.hispi_bits * self.config.buffersize))
        self.aligned = Signal(reset=False)

    def get_words(self, count, bit_offset=None, word_offset=0):
        if bit_offset is None:
            bit_offset = self.bit_offset

        try:
            assert word_offset + count + ceil(bit_offset / self.config.hispi_bits) < self.config.buffersize
        # catch when bit_offset / word_offset is Signal
        except TypeError:
            pass

        return self.buf.slice(start=bit_offset + self.config.hispi_bits * word_offset,
                              length=count * self.config.hispi_bits)

    def get_aligned_words(self, count, offset=0):
        return self.get_words(count=count,
                              bit_offset=self.bit_offset,
                              word_offset=self.word_offset + offset)

    def is_aligned(self):
        return self.aligned


def hispi_sync_code(config):
    return 2 ** (config.hispi_bits) - 1


@hispi_module
class HispiLane(HispiBase):
    def __init__(self, buf):
        # TODO(robin): good style? or bad style?
        # assert type(buf) is HispiBuffer

        sync_code = hispi_sync_code(self.config)

        for offset in range(self.config.hispi_bits):
            self.sync += If(buf.get_words(count=3, bit_offset=offset) == sync_code,
                            buf.bit_offset.eq(offset))


@hispi_module
class HispiLaneWordAligner(HispiBase):
    def __init__(self, lane0, lane):
        middle = self.config.buffersize // 2 - 1
        sync_code = hispi_sync_code(self.config)

        is_sync_code = lambda l, offset=0: l.get_words(count=3, word_offset=offset) == sync_code

        self.sync += If(is_sync_code(lane0, middle),
                        [If(is_sync_code(lane, offset),
                            lane.word_offset.eq(offset),
                            lane.aligned.eq(True))
                         for offset in range(self.config.buffersize - 2)])


@hispi_module
class HispiWordAligner(HispiBase):
    def __init__(self, bufs):
        assert len(bufs) == self.config.num_lanes

        # TODO(robin): this is a bit wonkey and alignes the lanes relative to lane 0
        #              is there a more "symmetrical" solution?
        #              one possibility is starting a buffer, when a lane is aligned and growing the buffer until all lanes are aligned, then leaving the buffersize constant and taking the first word of each buffer makes all lanes aligned
        # buf not sure, if that is better, probably not (similar complexity)

        middle = self.config.buffersize // 2 - 1

        self.sync += bufs[0].word_offset.eq(middle)
        self.sync += bufs[0].aligned.eq(True)

        self.submodules += [HispiLaneWordAligner(config=self.config, lane0=bufs[0], lane=bufs[lane])
                            for lane in range(1, self.config.num_lanes)]


@hispi_module
class HispiDataConverter(HispiBase):
    def __init__(self, data_in):
        self.data_in = data_in  # [Signal(self.config.input_bits) for _ in self.config.num_lanes]
        self.data_out = [Signal(self.config.hispi_bits) for _ in range(self.config.num_lanes)]

        self.sync += [self.data_out[lane][:-self.config.input_bits].eq(self.data_out[lane][self.config.input_bits:]) for
                      lane in range(self.config.num_lanes)]

        self.sync += [self.data_out[lane][self.config.input_bits:].eq(self.data_in[lane]) for
                      lane in range(self.config.num_lanes)]





@hispi_module
class HispiDecoder(HispiBase):
    def __init__(self, lanes):
        assert self.config.buffersize >= 4

        self.frame_start = Signal(reset=False)

        self.data_valid = Signal(reset=False)

        data_actual_valid = Signal(reset=False)

        self.data_out = [Signal(self.config.output_bits) for _ in range(self.config.num_lanes)]
        found_frame_start = Signal(reset=False)

        padding_counter = Signal(bits_for(self.config.padding_size), reset=0)

        self.sync += If(self.data_valid, If(padding_counter + 1 < self.config.padding_size,
                                            padding_counter.eq(padding_counter + 1)).Else(padding_counter.eq(0)))

        self.comb += If(data_actual_valid, self.data_valid.eq(1)).Elif(padding_counter != 0,
                                                                       self.data_valid.eq(1)).Else(
            self.data_valid.eq(0))

        crc = [Buffer(2, self.config.hispi_bits) for i in range(self.config.hispi_bits)]

        aligned = reduce(lambda a, b: a & b, [lane.aligned for lane in lanes])

        handle_sync_code_coming = lambda: If(
            lanes[self.config.sync_lane].get_aligned_words(count=3, offset=1) == hispi_sync_code(self.config),
            NextState("SYNC_CODE0"))

        data = lambda lane: lane.get_aligned_words(count=1)

        sync_code = lambda: data(lanes[self.config.sync_lane])

        fsm = FSM("NO_ALIGN")
        self.submodules += fsm

        fsm.act("NO_ALIGN",
                If(aligned,
                   NextState("FILLER")
                   ))

        fsm.act("FILLER",
                handle_sync_code_coming())

        fsm.act("SYNC_CODE0",
                NextState("SYNC_CODE1"))

        fsm.act("SYNC_CODE1",
                NextState("SYNC_CODE2"))

        fsm.act("SYNC_CODE2",
                NextState("SYNC_CODE3"))

        fsm.act("SYNC_CODE3",
                Case(sync_code(), {
                    0b000000000001: NextState("PIXEL_DATA"),
                    0b000000001001: NextState("FILLER"),
                    # vblank, but we dont handle that yet (how would we handle that anyways?
                    0b000000010011: [NextValue(found_frame_start, 1), NextState("FILLER")],
                    # embedded data, but we don't handle that yet (contains a register dump of nearly all registers, we should use that when reading registers to reduce i2c bus contention
                    0b000000000011: [NextValue(found_frame_start, 1), NextState("PIXEL_DATA")],
                    0b000000010001: NextState("FILLER"),  # embedded data, see above
                    0b000000000101: NextState("CRC0"),  # TODO(robin) make this toggelable
                    0b000000000111: NextState("CRC0"),
                    "default": NextState("FILLER")}))  # maybe count the number of unhandled sync_codes?

        fsm.act("CRC0",
                [NextValue(crc[i][0], data(lanes[i])) for i in range(self.config.num_lanes)],
                NextState("CRC1"))

        # TODO(robin): acutally check the CRC
        fsm.act("CRC1",
                [NextValue(crc[i][1], data(lanes[i])) for i in range(self.config.num_lanes)],
                NextState("FILLER"))

        fsm.act("PIXEL_DATA",
                data_actual_valid.eq(1),

                self.frame_start.eq(found_frame_start),
                NextValue(found_frame_start, 0),

                [
                    self.data_out[i].eq(data(lanes[i]))
                    for i in range(self.config.num_lanes)
                ],

                handle_sync_code_coming())


@hispi_module
class DoubleUp(HispiBase):
    def __init__(self, data_in, data_valid_in, frame_start_in):
        data_bits = self.config.output_bits * self.config.num_lanes

        double_in = Signal((data_bits + 2) * 2)
        counter = Signal(2, reset=True)
        self.sync += If(data_valid_in,
                        If(counter == 2,
                           counter.eq(0)
                           ).Else(counter[0].eq(~counter[0]))
                        ).Else(counter.eq(2))

        self.sync += double_in[data_bits + 2:2 * data_bits + 2].eq(data_in)
        self.sync += double_in[-2].eq(data_valid_in)
        self.sync += double_in[-1].eq(frame_start_in)
        self.sync += double_in[:data_bits + 2].eq(double_in[data_bits + 2:])

        self.data_out = Signal(2 * data_bits, reset=0)
        self.data_valid = Signal(reset=0)
        self.frame_start = Signal(reset=0)

        self.comb += self.data_out.eq(Cat(double_in[:data_bits], double_in[data_bits + 2: 2 * data_bits + 2]))
        self.comb += self.data_valid.eq((double_in[data_bits + 1 - 1] | double_in[-2]) & counter[0])
        self.comb += self.frame_start.eq(double_in[data_bits + 2 - 1] | double_in[-1])


@hispi_module
class HispiRx(HispiBase):
    def __init__(self, data_in):
        converter = self.submodules.converter = ClockDomainsRenamer("hispi_half_word")(HispiDataConverter(self.config, data_in=data_in))

        self.cdc = [Signal(self.config.hispi_bits) for _ in range(self.config.num_lanes)]

        self.specials += [MultiReg(converter.data_out[i], self.cdc[i], "hispi_word") for i in range(self.config.num_lanes)]

        bufs = [ClockDomainsRenamer("hispi_word")(HispiBuffer(config=self.config, data_in=self.cdc[i])) for i in
                range(self.config.num_lanes)]
        self.submodules += bufs

        self.submodules += [ClockDomainsRenamer("hispi_word")(HispiLane(config=self.config, buf=bufs[i])) for i in
                            range(self.config.num_lanes)]
        self.submodules.hispi_word_aligner = ClockDomainsRenamer("hispi_word")(HispiWordAligner(config=self.config, bufs=bufs))

        decoder = self.decoder = self.submodules.decoder = ClockDomainsRenamer("hispi_word")(HispiDecoder(config=self.config, lanes=bufs))

        self.data_out = Signal(self.config.output_bits * self.config.num_lanes)

        self.comb += self.data_out.eq(Cat(*decoder.data_out))

        self.double_up = self.submodules.double_up = ClockDomainsRenamer("hispi_word")(
            DoubleUp(config=self.config, data_in=self.data_out, data_valid_in=decoder.data_valid,
                     frame_start_in=decoder.frame_start))



######

passthrough = lambda x: x


def test_hispi_rx():
    dut = HispiRx(config=hispi_config(**{"lane_inversion_map": [passthrough, passthrough, passthrough, passthrough]}))

    def testbench():
        f = open("test_data/test_convert3.txt")
        i = 0

        valid = False
        frame_start = False
        frame = b""
        pixel_count = 0
        skip = False

        for line in f:
            i += 1
            #            if i > 100000:
            #                break

            yield dut.data_in.eq(int(line.strip(), 2))
            #            print (format(int(line.strip(), 2), '0>24b'))

            #            print(format((yield dut.decoder.in_data), '0>48b'))
            #            print("state:", (yield dut.decoder._submodules[-1][1].state))

            if valid:
                pixel_count += 1

            if (yield dut.decoder.data_valid) == 1 and not valid:
                pixel_count += 1
                valid = True

            if (yield dut.decoder.data_valid) == 0 and valid:
                print(pixel_count)
                pixel_count = 0
                valid = False

            if (yield dut.decoder.frame_start) == 1 and frame_start and not skip:
                print(frame)
                break

            if (yield dut.decoder.frame_start) == 1 and skip:
                skip = False

            if (yield dut.decoder.frame_start) == 1:
                skip = True
                frame_start = True

            #            if frame_start and valid:
            #                frame += (yield dut.data_out).to_bytes(6, 'big')

            yield

    run_simulation(dut, testbench(), clocks={'sys': 10, 'hispi': (20, 10), 'half_hispi': (40, 20)},
                   vcd_name="hispi_rx.vcd")


def test_decoder():
    dut = HispiRx(config=hispi_config())

    def testbench():
        f = open("test_data/test_convert5.txt")
        i = 0

        valid = False
        frame_start = False
        frame = b""
        pixel_count = 0
        skip = False

        for line in f:
            i += 1
            #            if i > 100000:
            #                break

            #            print (format(int(line.strip(), 2), '0>24b'))

            #            print(format((yield dut.decoder.in_data), '0>48b'))
            #            print("state:", (yield dut.decoder._submodules[-1][1].state))

            yield dut.data_in.eq(int(line.strip().split(' ')[0], 2))

            if valid:
                pixel_count += 1

            if (yield dut.decoder.data_valid) == 1 and not valid:
                pixel_count += 1
                valid = True

            if (yield dut.decoder.data_valid) == 0 and valid:
                print(pixel_count)
                pixel_count = 0
                valid = False

            if (yield dut.decoder.frame_start) == 1 and frame_start and not skip:
                print(frame)
                break

            if (yield dut.decoder.frame_start) == 1 and skip:
                skip = False

            if (yield dut.decoder.frame_start) == 1:
                skip = True
                frame_start = True

            #            if frame_start and valid:
            #                frame += (yield dut.data_out).to_bytes(6, 'big')

            yield

    run_simulation(dut, testbench(), clocks={'sys': 10, 'hispi': (20, 0), 'half_hispi': (40, 00)},
                   vcd_name="hispi_rx.vcd")


@hispi_module
class TestDriver(HispiBase):
    def __init__(self):
        self.data_in = Signal(self.config.input_bits * self.config.num_lanes)
        self.submodules += HispiBuffer(config=self.config, data_in=self.data_in)


def test_buffer():
    dut = TestDriver(config=hispi_config({"lane_inversion_map": [passthrough, passthrough, passthrough, passthrough]}))

    def testbench():
        for i in range(128):
            yield dut.data_in.eq(i)
            yield

    run_simulation(dut, testbench(), vcd_name="buffer.vcd")