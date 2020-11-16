from lib.bus.stream.sim_util import write_to_stream, read_from_stream


def write_frame_to_stream(stream, frame):
    for y, line in enumerate(frame):
        for x, px in enumerate(line):
            yield from write_to_stream(
                stream, payload=int(px),
                line_last=(x == (len(line) - 1)),
                frame_last=(y == (len(frame) - 1)) & (x == (len(line) - 1)),
            )


def read_frame_from_stream(stream):
    frame = [[]]
    while True:
        px, line_last, frame_last = (yield from read_from_stream(stream, extract=("payload", "line_last", "frame_last")))
        frame[-1].append(px)
        if frame_last:
            return frame
        if line_last:
            frame.append([])
