from nmigen import *
from naps import PacketizedStream, ImageStream, VariableWidthStream
from naps.cores import BitStuffer, HuffmanEncoder, ZeroRleEncoder, ImageStream2PacketizedStream
from .wavelet import MultiStageWavelet2D


class WaveletCompressor(Elaboratable):
    """compresses an image stream using a wavelet compression algorithm"""
    def __init__(self, input: ImageStream, width, height):
        self.input = input
        self.width = width
        self.height = height

        max_input_word = 2**len(self.input.payload)
        self.possible_run_lengths = [2, 4, 8, 16, 32, 64, 128, 256]
        self.huffmann_frequencies = {
            **{k: 1 for k in range(max_input_word)},
            **{k: 10 for k in range(max_input_word, max_input_word + len(self.possible_run_lengths))}
        }

        self.output = PacketizedStream(self.input.payload.shape())

    def elaborate(self, platform):
        m = Module()

        wavelet = m.submodules.wavelet = MultiStageWavelet2D(self.input, self.width, self.height, stages=3)
        packetizer = m.submodules.packetizer = ImageStream2PacketizedStream(wavelet.output)

        bit_stuffing_input = VariableWidthStream(self.input.payload.shape(), reset_width=len(self.input.payload))
        with m.If(packetizer.output.is_hf):
            rle_input = PacketizedStream()
            m.d.comb += rle_input.connect_upstream(packetizer.output)
            rle = m.submodules.rle = ZeroRleEncoder(rle_input, self.possible_run_lengths)
            huffman = m.submodules.huffman = HuffmanEncoder(rle.output)
            m.d.comb += bit_stuffing_input.connect_upstream(huffman.output)
        with m.Else():
            m.d.comb += bit_stuffing_input.connect_upstream(packetizer.output)

        bit_stuffing = m.submodules.bit_stuffing = BitStuffer(bit_stuffing_input, len(self.output.payload))
        m.d.comb += self.output.connect_upstream(bit_stuffing.output)

        return m
