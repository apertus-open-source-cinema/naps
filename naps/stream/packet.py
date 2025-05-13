from amaranth.lib import data

class Packet(data.StructLayout):
    def __init__(self, payload_shape):
        return super().__init__({
                "p": payload_shape,
                "last": 1
        })
