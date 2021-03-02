from random import Random
from naps import write_to_stream, read_from_stream, do_nothing

__all__ = ["write_frame_to_stream", "read_frame_from_stream", "to_8bit_rgb", "crop"]


def write_frame_to_stream(stream, frame, timeout=100, pause=False):
    random = Random(0)
    for y, line in enumerate(frame):
        for x, px in enumerate(line):
            if (random.random() < 0.3) and pause:
                yield from do_nothing()
            yield from write_to_stream(
                stream, payload=int(px),
                timeout=timeout,
                line_last=(x == (len(line) - 1)),
                frame_last=(y == (len(frame) - 1)) & (x == (len(line) - 1)),
            )
        if (random.random() < 0.3) and pause:
            yield from do_nothing()


def read_frame_from_stream(stream, timeout=100, pause=False):
    random = Random(1)
    frame = [[]]
    while True:
        if (random.random() < 0.3) and pause:
            yield from do_nothing()
        px, line_last, frame_last = (yield from read_from_stream(stream, timeout=timeout,
                                                                 extract=("payload", "line_last", "frame_last")))
        frame[-1].append(px)
        if frame_last:
            return frame
        if line_last:
            frame.append([])


def to_8bit_rgb(image_24bit):
    return [
        [[px & 0xff, (px >> 8) & 0xff, (px >> 16) & 0xff] for px in line]
        for line in image_24bit
    ]


def crop(frame, left=0, right=0, top=0, bottom=0):
    return [line[left:len(line)-right] for line in frame[top:len(frame)-bottom]]
