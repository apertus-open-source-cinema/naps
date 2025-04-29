import copy
from collections import OrderedDict
from amaranth import *
from amaranth.lib import stream, wiring, data
from amaranth.lib.wiring import In, Out
# from naps import Bundle, UPWARDS, DOWNWARDS

__all__ = ["Stream", "PacketizedStream"]

class Bundle:
    ...
class UPWARDS:
    ...

class DOWNWARDS:
    ...

class Stream(Bundle):
    """
    A stream is everything that inherits from `Bundle` and has a ready@UPWARDS, a valid@DOWNWARDS.
    Stream Sinks (downstream) pull ready high if they can accept data and stream Sources (upstream) pull valid
    high if they have data to offer. Both ready-before-valid and valid-before-ready are allowed.
    A successful data transfer on the stream happens if ready and valid are 1 during a cycle.

    Optionally Streams may have any number of DOWNWARDS Signals, that carry actual payload and/or out-of-band signaling
    (e.g. last or first) as their payload.

    Streams have to implement a clone() methods that returns a Stream that is shaped just like the original stream
    but not connected to it.

    This is the base Stream class that is pretty much useless on its own. Other Classes are implementing Streams that
    are useful for real use-cases. Probably you are looking for `BasicStream`
    """

    def __init__(self, name=None, src_loc_at=1):
        super().__init__(name=name, src_loc_at=1 + src_loc_at)

        self.ready = Signal() @ UPWARDS
        self.valid = Signal() @ DOWNWARDS

    def clone(self, name=None, src_loc_at=1):
        new_stream = self.__class__.__new__(self.__class__)
        Stream.__init__(new_stream, name=name, src_loc_at=1 + src_loc_at)

        for k, signal in self.payload_signals.items():
            setattr(new_stream, k, Signal(signal.shape()) @ DOWNWARDS)
        new_stream._directions = copy.deepcopy(self._directions)
        return new_stream

    @property
    def payload_signals(self):
        return OrderedDict((k, self[k]) for k, direction in self._directions.items() if k != "valid" and direction == DOWNWARDS)


# class BasicStream(Stream):
#     """A basic stream that carries a payload"""
# 
#     def __init__(self, payload_shape, name=None, src_loc_at=1):
#         super().__init__(name=name, src_loc_at=1 + src_loc_at)
#         self.payload = Signal(payload_shape) @ DOWNWARDS
# 
#     @property
#     def out_of_band_signals(self):
#         return OrderedDict((k, v) for k, v in self.payload_signals.items() if k != "payload")


class SpicyStreamSignature(wiring.Signature):
    """
    SpicyStream is our stream that can hold out-of-bands signals. 
    The most common example for this is ``last`` that indicates the end of a packet.
    Do not use this directly but rather inherit from it (see PacketizedStreamSignature for an example)
    """
    def __init__(self, payload_shape, interface_type=None, **out_of_band):
        super().__init__({
            "payload": Out(data.StructLayout({
                "v": payload_shape,
                **out_of_band
            })),
            "valid": Out(1),
            "ready": In(1)
        })
        self._oob = out_of_band
        self._interface_type = SpicyStreamInterface if interface_type is None else interface_type

    def create(self, *, path=None, src_loc_at=0):
        return self._interface_type(self, self._oob, path=path, src_loc_at=1 + src_loc_at)

class SpicyStreamInterface(wiring.PureInterface):
    def __init__(self, sig, oob, *, path, src_loc_at):
        super().__init__(sig, path=path, src_loc_at=1 + src_loc_at)
        self._oob = oob

    @property
    def p(self): 
        #print( super(SpicyStreamInterface, self).__dict__)
        return super(SpicyStreamInterface, self).__dict__["payload"]

    @property
    def _out_of_band_signals(self):
        return {
            n: getattr(self.p, n) for n in self._oob.keys()
        }

    @property
    def _real_payload(self):
        return self.p.v


def real_payload(stream):
    if hasattr(stream, "_real_payload"):
        return stream._real_payload
    else:
        return stream.p

def out_of_band_signals(stream):
    if hasattr(stream, "_out_of_band_signals"):
        return stream._out_of_band_signals
    else:
        return {}


class PacketizedStreamInterface(SpicyStreamInterface):
    def __init__(self, sig, oob, *, path=None, src_loc_at=0):
        super().__init__(sig, oob, path=path, src_loc_at=1 + src_loc_at)

    @property
    def p(self): return super().p.v

    #@property
    #def payload(self): 
        ## TODO(robin): add a fucking warning here
        #return super().p.v
    
    @property
    def last(self): return super().p.last


class PacketizedStreamSignature(SpicyStreamSignature):
    """
    A stream that carries a payload and can separate Packets via a last signal that is asserted on the
    last word of a packet
    """

    def __init__(self, payload_shape):
        super().__init__(payload_shape, PacketizedStreamInterface, last=1)




if __name__ == "__main__":
    a = PacketizedStreamSignature(32)
    intf = a.create()
    print(intf.last)
    print(intf.p)
    print(intf.payload)
    print(intf.ready)
    print(intf.valid)

    other = SpicyStreamSignature(32, last=1).create()

    m = Module()
    wiring.connect(m, wiring.flipped(intf), other)