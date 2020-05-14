from nmigen import Signal


class TristateIo:
    i: Signal
    o: Signal
    oe: Signal
